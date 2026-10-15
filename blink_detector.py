import cv2
import mediapipe as mp
import numpy as np
import time
import csv
from collections import deque
import pandas as pd
import matplotlib.pyplot as plt

CAMERA_ID = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

CALIBRATION_SECONDS = 2.0
SMOOTHING_WINDOW = 3
EAR_THRESHOLD_FACTOR = 0.70
MIN_BLINK_DURATION = 0.03
MAX_BLINK_DURATION = 1.2

FALLBACK_EAR_THRESHOLD = 0.21

LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]

def euclidean(a, b):
    return np.linalg.norm(np.array(a) - np.array(b))

def eye_aspect_ratio(eye_points):
    p1, p2, p3, p4, p5, p6 = eye_points
    A = euclidean(p2, p6)
    B = euclidean(p3, p5)
    C = euclidean(p1, p4)
    return (A + B) / (2.0 * C) if C > 0 else 0.0

def landmark_list_to_points(landmarks, indices, img_w, img_h):
    return [(int(landmarks[idx].x * img_w), int(landmarks[idx].y * img_h)) for idx in indices]

def run_blink_detection():
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True,
                                      min_detection_confidence=0.5,
                                      min_tracking_confidence=0.5)

    cap = cv2.VideoCapture(CAMERA_ID)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    ear_history = deque(maxlen=SMOOTHING_WINDOW)
    blink_log = []
    blink_count = 0
    blink_in_progress = False
    blink_start_time = None

    calibrating = True
    calib_ears = []
    calib_start_time = time.time()

    print(f"[INFO] Starting webcam. Calibrating for {CALIBRATION_SECONDS:.1f}s...")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Camera not available.")
            break

        img_h, img_w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        ear = None
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            left_pts = landmark_list_to_points(landmarks, LEFT_EYE_IDX, img_w, img_h)
            right_pts = landmark_list_to_points(landmarks, RIGHT_EYE_IDX, img_w, img_h)
            ear = (eye_aspect_ratio(left_pts) + eye_aspect_ratio(right_pts)) / 2.0

        if calibrating:
            if ear is not None:
                calib_ears.append(ear)
            if time.time() - calib_start_time >= CALIBRATION_SECONDS:
                if len(calib_ears) >= 5:
                    baseline_open_ear = float(np.median(calib_ears))
                    ear_threshold = baseline_open_ear * EAR_THRESHOLD_FACTOR
                    print(f"[INFO] Calibration complete. baseline EAR = {baseline_open_ear:.3f}, threshold = {ear_threshold:.3f}")
                else:
                    baseline_open_ear = None
                    ear_threshold = FALLBACK_EAR_THRESHOLD
                    print(f"[WARN] Calibration insufficient, using fallback threshold {ear_threshold:.3f}")
                calibrating = False
        else:
            ear_smooth = None
            if ear is not None:
                ear_history.append(ear)
                ear_smooth = float(np.mean(ear_history))

            if ear_smooth is not None and ear_smooth < ear_threshold:
                if not blink_in_progress:
                    blink_in_progress = True
                    blink_start_time = time.time()
            else:
                if blink_in_progress:
                    blink_end_time = time.time()
                    duration = blink_end_time - blink_start_time
                    if MIN_BLINK_DURATION <= duration <= MAX_BLINK_DURATION:
                        blink_count += 1
                        blink_log.append({
                            'blink_id': blink_count,
                            'timestamp': blink_end_time - calib_start_time,
                            'duration': duration
                        })
                        print(f"[BLINK] #{blink_count} duration={duration:.3f}s")
                    blink_in_progress = False
                    blink_start_time = None

            elapsed = time.time() - calib_start_time
            bpm = (blink_count / elapsed) * 60.0 if elapsed > 0 else 0.0

            cv2.putText(frame, f"Blinks: {blink_count}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 0), 2)
            cv2.putText(frame, f"Blinks/min: {bpm:.1f}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 200), 2)

        if calibrating:
            cv2.putText(frame, "Calibrating... look at camera", (10, img_h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        cv2.imshow("Blink Monitor", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    if blink_log:
        df = pd.DataFrame(blink_log)
        df.to_csv("blink_log.csv", index=False)
        print(f"[INFO] Saved blink log with {len(df)} blinks to blink_log.csv")
        return df
    else:
        print("[INFO] No blinks detected.")
        return None

def analyze_blinks(df):
    NORMAL_BLINK_MIN = 0.08
    NORMAL_BLINK_MAX = 0.6
    NORMAL_RATE_MIN = 10
    NORMAL_RATE_MAX = 20

    total_blinks = len(df)
    session_time = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]) / 60
    blink_rate = total_blinks / session_time if session_time > 0 else 0

    short_blinks = df[df["duration"] < NORMAL_BLINK_MIN]
    long_blinks = df[df["duration"] > NORMAL_BLINK_MAX]
    abnormal_blinks = len(short_blinks) + len(long_blinks)
    duration_std = df["duration"].std()

    print("\n===== Blink Monitoring Report =====")
    print(f"Session Duration: {session_time:.2f} minutes")
    print(f"Total Blinks: {total_blinks}")
    print(f"Blink Rate: {blink_rate:.1f} blinks/min (Normal: {NORMAL_RATE_MIN}-{NORMAL_RATE_MAX})")
    print(f"Short Blinks (<{NORMAL_BLINK_MIN}s): {len(short_blinks)}")
    print(f"Prolonged Blinks (>{NORMAL_BLINK_MAX}s): {len(long_blinks)}")
    print(f"Blink Duration Variability (std): {duration_std:.3f}s")

    if blink_rate < NORMAL_RATE_MIN:
        print("Low blink rate -> possible Parkinsonism or fatigue")
    elif blink_rate > NORMAL_RATE_MAX:
        print("High blink rate -> possible ocular irritation / stress")

    if len(short_blinks) > 0:
        print("Very short blinks -> possible neuromuscular weakness")
    if len(long_blinks) > 0:
        print("Prolonged blinks -> fatigue/neurological issue")
    if duration_std > 0.15:
        print("High blink variability -> possible impairment")
    print("==================================\n")

    plt.figure(figsize=(12, 6))

    plt.subplot(1, 3, 1)
    plt.plot(df["timestamp"], df["duration"], marker='o')
    plt.axhline(y=NORMAL_BLINK_MIN, color='r', linestyle='--', label="Min Normal")
    plt.axhline(y=NORMAL_BLINK_MAX, color='r', linestyle='--', label="Max Normal")
    plt.xlabel("Time (s)")
    plt.ylabel("Blink Duration (s)")
    plt.title("Blink Durations Over Time")
    plt.legend()

    plt.subplot(1, 3, 2)
    plt.hist(df["duration"], bins=20, color='skyblue', edgecolor='black')
    plt.axvline(NORMAL_BLINK_MIN, color='r', linestyle='--')
    plt.axvline(NORMAL_BLINK_MAX, color='r', linestyle='--')
    plt.xlabel("Blink Duration (s)")
    plt.ylabel("Count")
    plt.title("Histogram of Blink Durations")

    plt.subplot(1, 3, 3)
    counts = [total_blinks - abnormal_blinks, abnormal_blinks]
    labels = ["Normal", "Abnormal"]
    plt.bar(labels, counts, color=["green", "red"])
    plt.title("Normal vs Abnormal Blinks")

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    df = run_blink_detection()
    if df is not None:
        analyze_blinks(df)
