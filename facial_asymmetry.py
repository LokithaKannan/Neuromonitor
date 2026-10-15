#!/usr/bin/env python3
import cv2
import mediapipe as mp
import numpy as np
import time
import csv
from collections import deque, namedtuple

CAMERA_ID = 0
FRAME_W = 640
FRAME_H = 480
CALIBRATE_SECONDS = 3.0
SMOOTH_WINDOW = 5
ASYM_THRESHOLD = 0.15
CONSEC_FRAMES_TO_ALERT = 6
CONSEC_FRAMES_TO_CLEAR = 6
MICRO_THRESHOLD = 0.30
MICRO_COOLDOWN_FRAMES = 12

SAVE_CSV = True
ASYM_LOG_PATH = "asymmetry_events.csv"
MICRO_LOG_PATH = "microexpression_events.csv"

W_EYE = 0.6
W_MOUTH = 0.25
W_BROW = 0.15

LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]
MOUTH_LEFT = 61
MOUTH_RIGHT = 291
BROW_LEFT = 70
BROW_RIGHT = 300
OUTER_LEFT_EYE_CORNER = 33
OUTER_RIGHT_EYE_CORNER = 263

def euclid(a, b):
    return np.linalg.norm(np.array(a) - np.array(b))

def lm_to_point(lm, idx, w, h):
    return (int(lm[idx].x * w), int(lm[idx].y * h))

def compute_ear_from_indices(lm, indices, w, h):
    p = [lm_to_point(lm, i, w, h) for i in indices]
    A = euclid(p[1], p[5])
    B = euclid(p[2], p[4])
    C = euclid(p[0], p[3])
    return (A + B) / (2.0 * C) if C > 1e-6 else 0.0

def main():
    mp_face = mp.solutions.face_mesh
    face_mesh = mp_face.FaceMesh(max_num_faces=1, refine_landmarks=True,
                                min_detection_confidence=0.5, min_tracking_confidence=0.5)

    cap = cv2.VideoCapture(CAMERA_ID)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

    eye_left_buf = deque(maxlen=SMOOTH_WINDOW)
    eye_right_buf = deque(maxlen=SMOOTH_WINDOW)
    mouth_asym_buf = deque(maxlen=SMOOTH_WINDOW)
    brow_asym_buf = deque(maxlen=SMOOTH_WINDOW)
    asym_score_buf = deque(maxlen=SMOOTH_WINDOW)

    calib_eye_left = []
    calib_eye_right = []
    calib_mouth_asym = []
    calib_brow_asym = []
    start_time = time.time()

    consec_above = 0
    consec_below = 0
    asym_event_active = False
    asym_event_start = None
    asym_events = []

    micro_events = []
    micro_cooldown = 0
    prev_mouth_asym = None
    prev_brow_asym = None

    FrameStat = namedtuple("FrameStat", ["time", "eye_left", "eye_right", "mouth_asym", "brow_asym", "asym_score"])

    print(f"[INFO] Starting. Calibrating for {CALIBRATE_SECONDS:.1f}s - keep a neutral face facing the camera.")
    frame_count = 0
    last_print = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Camera read failed.")
                break
            frame_count += 1
            t = time.time()

            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = face_mesh.process(rgb)

            if res.multi_face_landmarks:
                lm = res.multi_face_landmarks[0].landmark

                left_ear = compute_ear_from_indices(lm, LEFT_EYE_IDX, w, h)
                right_ear = compute_ear_from_indices(lm, RIGHT_EYE_IDX, w, h)
                eye_asym = abs(left_ear - right_ear) / max(left_ear, right_ear, 1e-6)

                ml = lm_to_point(lm, MOUTH_LEFT, w, h)
                mr = lm_to_point(lm, MOUTH_RIGHT, w, h)
                mouth_width = euclid(ml, mr)
                mouth_vert_diff = abs(ml[1] - mr[1])
                mouth_asym = mouth_vert_diff / max(mouth_width, 1e-6)

                bl = lm_to_point(lm, BROW_LEFT, w, h)
                br = lm_to_point(lm, BROW_RIGHT, w, h)
                inter_ocular = euclid(lm_to_point(lm, OUTER_LEFT_EYE_CORNER, w, h),
                                      lm_to_point(lm, OUTER_RIGHT_EYE_CORNER, w, h))
                brow_asym = abs(bl[1] - br[1]) / max(inter_ocular, 1e-6)

                eye_left_buf.append(left_ear); eye_right_buf.append(right_ear)
                mouth_asym_buf.append(mouth_asym); brow_asym_buf.append(brow_asym)

                s_left = np.mean(eye_left_buf)
                s_right = np.mean(eye_right_buf)
                s_mouth = np.mean(mouth_asym_buf)
                s_brow = np.mean(brow_asym_buf)

                asym_score = W_EYE * (abs(s_left - s_right) / max(s_left, s_right, 1e-6)) \
                             + W_MOUTH * s_mouth + W_BROW * s_brow
                asym_score_buf.append(asym_score)

                if time.time() - start_time < CALIBRATE_SECONDS:
                    calib_eye_left.append(left_ear); calib_eye_right.append(right_ear)
                    calib_mouth_asym.append(mouth_asym); calib_brow_asym.append(brow_asym)
                    cv2.putText(frame, "Calibrating... keep neutral face", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                else:
                    base_eye_left = np.median(calib_eye_left) if calib_eye_left else s_left
                    base_eye_right = np.median(calib_eye_right) if calib_eye_right else s_right
                    base_mouth = np.median(calib_mouth_asym) if calib_mouth_asym else s_mouth
                    base_brow = np.median(calib_brow_asym) if calib_brow_asym else s_brow

                    cur_asym = np.mean(asym_score_buf)
                    if cur_asym > ASYM_THRESHOLD:
                        consec_above += 1
                        consec_below = 0
                    else:
                        consec_below += 1
                        consec_above = 0

                    if consec_above >= CONSEC_FRAMES_TO_ALERT and not asym_event_active:
                        asym_event_active = True
                        asym_event_start = t
                        asym_event_max = cur_asym
                        print(f"[EVENT] Asymmetry START at {t:.1f}s (score {cur_asym:.3f})")
                    if asym_event_active:
                        asym_event_max = max(asym_event_max, cur_asym)
                        if consec_below >= CONSEC_FRAMES_TO_CLEAR:
                            asym_event_end = t
                            asym_events.append({
                                "start": asym_event_start,
                                "end": asym_event_end,
                                "duration_s": asym_event_end - asym_event_start,
                                "max_score": asym_event_max
                            })
                            print(f"[EVENT] Asymmetry END at {asym_event_end:.1f}s (dur {asym_event_end - asym_event_start:.2f}s, max {asym_event_max:.3f})")
                            asym_event_active = False
                            asym_event_start = None

                    if prev_mouth_asym is not None and micro_allowed(mouth_asym, prev_mouth_asym, MICRO_THRESHOLD):
                        if micro_cooldown == 0:
                            micro_events.append({"time": t, "type": "mouth", "value": mouth_asym})
                            micro_cooldown = MICRO_COOLDOWN_FRAMES
                            cv2.putText(frame, "Micro-expression (mouth)", (10, 140),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    if prev_brow_asym is not None and micro_allowed(brow_asym, prev_brow_asym, MICRO_THRESHOLD):
                        if micro_cooldown == 0:
                            micro_events.append({"time": t, "type": "brow", "value": brow_asym})
                            micro_cooldown = MICRO_COOLDOWN_FRAMES
                            cv2.putText(frame, "Micro-expression (brow)", (10, 170),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                    prev_mouth_asym = s_mouth
                    prev_brow_asym = s_brow

                    if micro_cooldown > 0:
                        micro_cooldown -= 1

                    cv2.putText(frame, f"asym_score: {cur_asym:.3f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
                    cv2.putText(frame, f"eye_asym: {eye_asym:.3f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,0), 2)
                    cv2.putText(frame, f"mouth_asym: {s_mouth:.3f}", (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,0), 2)
                    cv2.putText(frame, f"brow_asym: {s_brow:.3f}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,0), 2)

                    if asym_event_active:
                        cv2.putText(frame, "SUSTAINED FACIAL ASYMMETRY", (10, FRAME_H - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 3)

                eye_pts = [lm_to_point(lm, i, w, h) for i in (LEFT_EYE_IDX + RIGHT_EYE_IDX)]
                for p in eye_pts:
                    cv2.circle(frame, p, 1, (0,255,0), -1)
                cv2.circle(frame, ml, 2, (255,0,0), -1)
                cv2.circle(frame, mr, 2, (255,0,0), -1)
                cv2.circle(frame, bl, 2, (0,0,255), -1)
                cv2.circle(frame, br, 2, (0,0,255), -1)

            else:
                cv2.putText(frame, "No face detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)

            cv2.imshow("Facial Asymmetry (improved)", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break

            if time.time() - last_print > 5:
                last_print = time.time()

    finally:
        cap.release()
        cv2.destroyAllWindows()
        if asym_event_active:
            tnow = time.time()
            asym_events.append({
                "start": asym_event_start,
                "end": tnow,
                "duration_s": tnow - asym_event_start,
                "max_score": asym_event_max
            })
            print(f"[EVENT] Asymmetry END at {tnow:.1f}s (dur {tnow - asym_event_start:.2f}s, max {asym_event_max:.3f})")

        print("\n===== SUMMARY =====")
        if len(asym_events) == 0:
            print("No sustained asymmetry events detected.")
        else:
            print(f"Sustained asymmetry events: {len(asym_events)}")
            for i,e in enumerate(asym_events,1):
                print(f" {i}. start={e['start']:.1f}s end={e['end']:.1f}s dur={e['duration_s']:.2f}s max_score={e['max_score']:.3f}")

        print(f"Micro-expressions counted: {len(micro_events)}")
        if micro_events:
            for i,m in enumerate(micro_events,1):
                print(f" {i}. t={m['time']:.1f}s type={m['type']} val={m['value']:.3f}")

        avg_asym = np.mean(list(asym_score_buf)) if len(asym_score_buf)>0 else 0.0
        print(f"Average asymmetry score (smoothed): {avg_asym:.3f}")
        print("===================\n")

        if SAVE_CSV:
            if asym_events:
                with open(ASYM_LOG_PATH, "w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=["start","end","duration_s","max_score"])
                    w.writeheader()
                    w.writerows(asym_events)
                print(f"[SAVED] {ASYM_LOG_PATH}")

            if micro_events:
                with open(MICRO_LOG_PATH, "w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=["time","type","value"])
                    w.writeheader()
                    w.writerows(micro_events)
                print(f"[SAVED] {MICRO_LOG_PATH}")

def micro_allowed(cur, prev, threshold):
    if prev is None:
        return False
    denom = max(prev, 1e-6)
    return abs(cur - prev) / denom > threshold

if __name__ == "__main__":
    main()
