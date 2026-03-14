"""Generate synthetic fatigue training data."""
import csv
import random
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def generate_session(session_id: int, n_reps: int, degradation_type: str):
    """Generate a single session with a degradation pattern."""
    rows = []
    base_rom = random.uniform(70, 120)
    base_duration = random.uniform(1.5, 3.0)
    base_symmetry = random.uniform(0.9, 1.0)

    for rep in range(1, n_reps + 1):
        progress = rep / n_reps

        if degradation_type == "none":
            rom = base_rom + random.gauss(0, 2)
            duration = base_duration + random.gauss(0, 0.1)
            symmetry = base_symmetry + random.gauss(0, 0.02)
            fatigued = 0
        elif degradation_type == "linear":
            rom = base_rom * (1 - 0.3 * progress) + random.gauss(0, 2)
            duration = base_duration * (1 + 0.4 * progress) + random.gauss(0, 0.1)
            symmetry = base_symmetry * (1 - 0.25 * progress) + random.gauss(0, 0.02)
            fatigued = 1 if progress > 0.4 else 0
        elif degradation_type == "sudden":
            threshold = random.uniform(0.5, 0.8)
            if progress < threshold:
                rom = base_rom + random.gauss(0, 2)
                duration = base_duration + random.gauss(0, 0.1)
                symmetry = base_symmetry + random.gauss(0, 0.02)
                fatigued = 0
            else:
                rom = base_rom * 0.65 + random.gauss(0, 3)
                duration = base_duration * 1.5 + random.gauss(0, 0.2)
                symmetry = base_symmetry * 0.7 + random.gauss(0, 0.03)
                fatigued = 1
        elif degradation_type == "gradual_recovery":
            if progress < 0.6:
                rom = base_rom * (1 - 0.25 * progress) + random.gauss(0, 2)
                duration = base_duration * (1 + 0.3 * progress) + random.gauss(0, 0.1)
                symmetry = base_symmetry * (1 - 0.2 * progress) + random.gauss(0, 0.02)
                fatigued = 1 if progress > 0.35 else 0
            else:
                recovery = (progress - 0.6) / 0.4
                rom = base_rom * (0.85 + 0.1 * recovery) + random.gauss(0, 2)
                duration = base_duration * (1.18 - 0.1 * recovery) + random.gauss(0, 0.1)
                symmetry = base_symmetry * (0.88 + 0.08 * recovery) + random.gauss(0, 0.02)
                fatigued = 0
        else:
            raise ValueError(f"Unknown degradation type: {degradation_type}")

        rom = max(rom, 10)
        duration = max(duration, 0.5)
        symmetry = max(0.0, min(1.0, symmetry))

        rows.append({
            "session_id": session_id,
            "rep_number": rep,
            "rom_degrees": round(rom, 2),
            "duration_sec": round(duration, 3),
            "symmetry_score": round(symmetry, 4),
            "avg_velocity": round(rom / max(duration, 0.01), 2),
            "smoothness": round(random.uniform(0.6, 1.0), 4),
            "fatigued": fatigued,
            "degradation_type": degradation_type,
        })

    return rows


def main():
    random.seed(42)
    all_rows = []
    session_id = 0

    patterns = [
        ("none", 50),
        ("linear", 60),
        ("sudden", 50),
        ("gradual_recovery", 50),
    ]

    for pattern, count in patterns:
        for _ in range(count):
            n_reps = random.randint(8, 25)
            rows = generate_session(session_id, n_reps, pattern)
            all_rows.extend(rows)
            session_id += 1

    output_path = DATA_DIR / "synthetic_fatigue_training.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_rows[0].keys())
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Generated {len(all_rows)} rows across {session_id} sessions -> {output_path}")


if __name__ == "__main__":
    main()
