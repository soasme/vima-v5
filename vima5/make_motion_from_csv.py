import json
import csv
import sys

def main():
    reader = csv.DictReader(sys.stdin)
    data = {
        "version": "1.0",
        "name": "walk",
        "fps": 30,
        "keyframes": [],
    }
    for row in reader:
        keyframe = {
            "duration": float(row['duration']),
            "transition": row['transition'],
            "rotations": [
                {
                    "point_id": "left_shoulder",
                    "angle": float(row['left_shoulder']),
                },
                {
                    "point_id": "right_shoulder",
                    "angle": float(row['right_shoulder']),
                },
                {
                    "point_id": "left_hip",
                    "angle": float(row['left_hip']),
                },
                {
                    "point_id": "right_hip",
                    "angle": float(row['right_hip']),
                },
                {
                    "point_id": "left_knee",
                    "angle": float(row['left_knee']),
                },
                {
                    "point_id": "right_knee",
                    "angle": float(row['right_knee']),
                },
                {
                    "point_id": "left_ankle",
                    "angle": float(row['left_ankle']),
                },
                {
                    "point_id": "right_ankle",
                    "angle": float(row['right_ankle']),
                },
                {
                    "point_id": "left_elbow",
                    "angle": float(row['left_elbow']),
                },
                {
                    "point_id": "right_elbow",
                    "angle": float(row['right_elbow']),
                },
                {
                    "point_id": "left_wrist",
                    "angle": float(row['left_wrist']),
                },
                {
                    "point_id": "right_wrist",
                    "angle": float(row['right_wrist']),
                },
            ]
        }
        data['keyframes'].append(keyframe)

    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
