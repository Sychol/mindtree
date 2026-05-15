from __future__ import annotations

import re


def synonym_key(value: str) -> str:
    return re.sub(r"[\s\W_]+", "", value.strip().lower())


_SYNONYM_GROUPS: dict[str, tuple[str, ...]] = {
    "쉼": ("쉬고싶다", "쉬어가기", "휴식", "쉬다", "쉬어가다", "쉬어가"),
    "괜찮아": ("괜찮다", "괜찮아", "괜찮습니다", "괜찮아요"),
    "긴장": ("불안", "초조", "긴장됨", "긴장감", "떨림"),
    "피로": ("피곤", "지침", "소진", "번아웃", "지쳤다", "지쳐"),
    "버팀": ("버텼다", "견뎠다", "버티기", "버텨", "견딤"),
    "잠": ("잠이안와", "잠이안와요", "불면", "잠못잠", "잠을못자"),
    "답답함": ("답답", "답답함", "가슴답답", "가슴이답답"),
    "호흡": ("호흡", "숨쉬기", "숨고르기", "숨을쉬다"),
    "감사": ("고마움", "감사해", "감사합니다", "고마워"),
    "응원": ("응원해", "힘내", "힘", "응원합니다"),
    "위로": ("위로", "토닥임", "토닥여"),
    "회복": ("회복", "나아짐", "다시일어남"),
    "안정": ("안정", "차분함", "진정"),
    "산책": ("걷기", "산책하기", "걸어보기"),
    "물마시기": ("물마시기", "물마셔", "물한잔"),
}


SYNONYM_MAP: dict[str, str] = {}
for canonical, aliases in _SYNONYM_GROUPS.items():
    SYNONYM_MAP[synonym_key(canonical)] = canonical
    for alias in aliases:
        SYNONYM_MAP[synonym_key(alias)] = canonical


def apply_synonym(value: str) -> str:
    key = synonym_key(value)
    return SYNONYM_MAP.get(key, value.strip())
