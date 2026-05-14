RAW_FIELDS = [
    "prov",
    "city",
    "district",
    "devzone",
    "town",
    "community",
    "village_group",
    "road",
    "roadno",
    "poi",
    "subpoi",
    "houseno",
    "cellno",
    "floorno",
    "roomno",
    "detail",
    "assist",
    "distance",
    "intersection",
    "redundant",
    "others",
]

LEVEL_DESCRIPTIONS = {
    "level_1": "省份",
    "level_2": "地市",
    "level_3": "区县",
    "level_4": "乡镇/街道",
    "level_5": "路/巷/街",
    "level_6": "门牌号码/路号",
    "level_7": "建筑物/小区/自然村",
    "level_8": "楼栋号",
    "level_9": "单元",
    "level_10": "楼层",
    "level_11": "户室号/村内户号",
}

LEVEL8_FIELDS = [f"level_{index}" for index in range(1, 9)]
LEVEL11_FIELDS = [f"level_{index}" for index in range(1, 12)]

VALIDATION_LEVEL_OPTIONS = LEVEL11_FIELDS
