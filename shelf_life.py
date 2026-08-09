# Total hari observasi per varietas
TOTAL_HARI = {
    "ambon": 17,
    "raja": 17,
}

# Daya simpan maksimal (dalam hari) pada suhu ruang
# Sesuaikan dengan data penelitian Anda
MAX_SHELF_LIFE = {
    "ambon": 14,   # Pisang Ambon biasanya lebih cepat matang
    "raja": 17,    # Pisang Raja lebih tahan
}

# Mapping Hari → Stage (5 tingkat kematangan)
HARI_TO_STAGE = {
    1: 1, 2: 1, 3: 1,           # H1-H3  → Stage 1
    4: 2, 5: 2, 6: 2,           # H4-H6  → Stage 2
    7: 3, 8: 3, 9: 3, 10: 3,    # H7-H10 → Stage 3
    11: 4, 12: 4, 13: 4,        # H11-H13 → Stage 4
    14: 5, 15: 5, 16: 5, 17: 5, # H14-H17 → Stage 5
}

SUB_KATEGORI = {
    1: "Mentah Hijau",
    2: "Hijau Kuning",
    3: "Matang Pohon",
    4: "Matang Optimal",
    5: "Matang Lanjut",
}


def estimate_shelf_life(label):
    """
    Input: label seperti 'ambon_H5' atau 'raja_H12'
    Output: dict dengan info shelf life
    """
    parts = label.split("_")
    variety = parts[0]          # "ambon" atau "raja"
    hari_str = parts[1]         # "H5"
    current_day = int(hari_str.replace("H", ""))

    max_shelf = MAX_SHELF_LIFE.get(variety, 17)
    remaining_days = max(0, max_shelf - current_day)

    stage = HARI_TO_STAGE.get(current_day, 3)
    sub_kategori = SUB_KATEGORI.get(stage, "Unknown")

    return {
        "variety": variety.capitalize(),  # "Ambon" atau "Raja"
        "variety_lower": variety,
        "current_day": current_day,
        "remaining_days": remaining_days,
        "max_shelf_life": max_shelf,
        "stage": stage,
        "sub_kategori": sub_kategori,
    }