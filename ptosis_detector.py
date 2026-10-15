import cv2
import mediapipe as mp
import numpy as np
import time

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

def eye_opening_ratio(landmarks, eye_indices, w, h):
    coords = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in eye_indices]
    vertical = np.linalg.norm(np.array(coords[1]) - np.array(coords[2]))
    horizontal = np.linalg.norm(np.array(coords[0]) - np.array(coords[3]))
    return vertical / horizontal if horizontal > 0 else 0

cap = cv2.VideoCapture(0)

baseline_left, baseline_right = [], []
start_time = time.time()
MONITOR_DURATION = 30
ptosis_alerted = False

print("[INFO] Starting ptosis monitoring for 30s...")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if results.multi_face_landmarks:
        for landmarks in results.multi_face_landmarks:
            left_ratio = eye_opening_ratio(landmarks.landmark, LEFT_EYE, w, h)
            right_ratio = eye_opening_ratio(landmarks.landmark, RIGHT_EYE, w, h)

            if time.time() - start_time < 5:
                baseline_left.append(left_ratio)
                baseline_right.append(right_ratio)
                cv2.putText(frame, "Calibrating...", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            else:
                base_left = np.median(baseline_left) if baseline_left else 0.3
                base_right = np.median(baseline_right) if baseline_right else 0.3

                left_drop = (left_ratio < base_left * 0.7)
                right_drop = (right_ratio < base_right * 0.7)

                cv2.putText(frame, f"L: {left_ratio:.2f} (base {base_left:.2f})", (30, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(frame, f"R: {right_ratio:.2f} (base {base_right:.2f})", (30, 130),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                if left_drop or right_drop:
                    cv2.putText(frame, "Possible Ptosis Detected", (50, 200),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                    ptosis_alerted = True

    cv2.imshow("Ptosis Detector", frame)

    if time.time() - start_time > MONITOR_DURATION:
        break

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()

if ptosis_alerted:
    print("Sustained eyelid drooping (ptosis) detected during monitoring.")
else:
    print("No significant ptosis detected.")
