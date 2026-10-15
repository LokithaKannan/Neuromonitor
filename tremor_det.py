import cv2
import mediapipe as mp
import time
import numpy as np
from collections import deque
import os

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

positions = deque(maxlen=150)

save_dir = "tremor_snapshots"
os.makedirs(save_dir, exist_ok=True)
saved_conditions = set()

def classify_tremor_severity(amplitude, frequency):
    if frequency < 1:
        return "No tremor"
    if frequency < 4:
        if amplitude < 2:
            return "Low-freq mild tremor"
        elif amplitude < 5:
            return "Low-freq moderate tremor"
        else:
            return "Low-freq severe tremor"
    elif 4 <= frequency <= 12:
        if amplitude < 2:
            return "Mild physiological tremor"
        elif amplitude < 5:
            return "Moderate physiological tremor"
        else:
            return "Severe physiological tremor"
    else:
        if amplitude < 2:
            return "High-freq mild tremor"
        elif amplitude < 5:
            return "High-freq moderate tremor"
        else:
            return "High-freq severe tremor"

def calculate_movement_amplitude(positions):
    if len(positions) < 2:
        return 0
    distances = []
    for i in range(1, len(positions)):
        x1, y1, _ = positions[i - 1]
        x2, y2, _ = positions[i]
        dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        distances.append(dist)
    return np.mean(distances)

def detect_tremor_frequency(positions):
    if len(positions) < 30:
        return 0
    timestamps = np.array([t for _, _, t in positions])
    xs = np.array([x for x, _, _ in positions])
    ys = np.array([y for _, y, _ in positions])
    xs = xs - np.mean(xs)
    ys = ys - np.mean(ys)
    time_uniform = np.linspace(timestamps[0], timestamps[-1], len(timestamps))
    x_interp = np.interp(time_uniform, timestamps, xs)
    y_interp = np.interp(time_uniform, timestamps, ys)
    signal = x_interp + y_interp
    fft = np.fft.fft(signal)
    freqs = np.fft.fftfreq(len(signal), d=(time_uniform[1] - time_uniform[0]))
    power = np.abs(fft) ** 2
    idx = (freqs > 0) & (freqs < 20)
    peak_freq = freqs[idx][np.argmax(power[idx])]
    return abs(peak_freq)

cap = cv2.VideoCapture(0)

with mp_hands.Hands(max_num_hands=1,
                    min_detection_confidence=0.6,
                    min_tracking_confidence=0.6) as hands:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)
        current_time = time.time()

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                x = int(hand_landmarks.landmark[8].x * w)
                y = int(hand_landmarks.landmark[8].y * h)
                positions.append((x, y, current_time))
                cv2.circle(frame, (x, y), 8, (0, 255, 0), -1)
                cv2.putText(frame, "8", (x + 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        if len(positions) >= 30:
            amp = calculate_movement_amplitude(positions)
            freq = detect_tremor_frequency(positions)
            severity = classify_tremor_severity(amp, freq)
            cv2.putText(frame, f"Freq: {freq:.2f} Hz", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(frame, f"Amp: {amp:.2f}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(frame, f"Severity: {severity}", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            if severity not in saved_conditions and severity != "No tremor":
                filename = severity.replace(" ", "_") + ".jpg"
                filepath = os.path.join(save_dir, filename)
                frame_copy = frame.copy()
                cv2.putText(frame_copy, severity, (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.imwrite(filepath, frame_copy)
                saved_conditions.add(severity)

        cv2.imshow("Tremor Detector", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
