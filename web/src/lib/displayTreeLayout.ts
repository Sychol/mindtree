import type { DisplayKeyword } from "../types/display";

export type PositionedKeyword = {
  text: string;
  weight: number;
  category?: string | null;
  left: number;
  top: number;
  fontSize: number;
  rotate: number;
  opacity: number;
  colorVariant: number;
};

type Slot = {
  left: number;
  top: number;
};

const CANOPY_LIMIT = 55;
const TRUNK_LIMIT = 28;

const CANOPY_SLOTS: Slot[] = [
  { left: 50, top: 50 },
  { left: 39, top: 48 },
  { left: 61, top: 49 },
  { left: 50, top: 35 },
  { left: 49, top: 65 },
  { left: 31, top: 58 },
  { left: 69, top: 59 },
  { left: 35, top: 34 },
  { left: 64, top: 34 },
  { left: 24, top: 47 },
  { left: 76, top: 47 },
  { left: 43, top: 23 },
  { left: 58, top: 23 },
  { left: 27, top: 72 },
  { left: 73, top: 72 },
  { left: 18, top: 60 },
  { left: 82, top: 60 },
  { left: 17, top: 36 },
  { left: 83, top: 36 },
  { left: 38, top: 77 },
  { left: 62, top: 78 },
  { left: 27, top: 25 },
  { left: 73, top: 25 },
  { left: 11, top: 50 },
  { left: 89, top: 50 },
  { left: 51, top: 14 },
  { left: 14, top: 72 },
  { left: 86, top: 72 },
  { left: 11, top: 28 },
  { left: 90, top: 29 },
  { left: 36, top: 13 },
  { left: 65, top: 13 },
  { left: 47, top: 84 },
  { left: 55, top: 87 },
  { left: 7, top: 62 },
  { left: 94, top: 62 },
  { left: 7, top: 40 },
  { left: 94, top: 40 },
  { left: 22, top: 82 },
  { left: 78, top: 83 },
  { left: 21, top: 16 },
  { left: 79, top: 17 },
  { left: 32, top: 88 },
  { left: 68, top: 89 },
  { left: 5, top: 51 },
  { left: 96, top: 52 },
  { left: 14, top: 18 },
  { left: 87, top: 19 },
  { left: 29, top: 8 },
  { left: 72, top: 8 },
  { left: 42, top: 93 },
  { left: 59, top: 94 },
  { left: 3, top: 72 },
  { left: 97, top: 72 },
  { left: 4, top: 25 },
  { left: 97, top: 25 },
];

const TRUNK_SLOTS: Slot[] = [
  { left: 50, top: 12 },
  { left: 42, top: 22 },
  { left: 59, top: 25 },
  { left: 50, top: 35 },
  { left: 38, top: 45 },
  { left: 62, top: 48 },
  { left: 49, top: 58 },
  { left: 34, top: 68 },
  { left: 66, top: 70 },
  { left: 50, top: 80 },
  { left: 30, top: 84 },
  { left: 72, top: 86 },
  { left: 43, top: 8 },
  { left: 58, top: 15 },
  { left: 35, top: 30 },
  { left: 66, top: 36 },
  { left: 43, top: 54 },
  { left: 58, top: 63 },
  { left: 37, top: 76 },
  { left: 62, top: 90 },
  { left: 50, top: 93 },
  { left: 28, top: 58 },
  { left: 74, top: 57 },
  { left: 31, top: 17 },
  { left: 70, top: 22 },
  { left: 25, top: 72 },
  { left: 76, top: 75 },
  { left: 50, top: 47 },
];

function textHash(value: string): number {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function sortKeywords(keywords: DisplayKeyword[], limit: number): DisplayKeyword[] {
  return [...keywords]
    .sort((left, right) => {
      if (right.weight !== left.weight) {
        return right.weight - left.weight;
      }
      return left.text.localeCompare(right.text, "ko-KR");
    })
    .slice(0, limit);
}

function scaleFontSize(weight: number, minWeight: number, maxWeight: number, minSize: number, maxSize: number): number {
  const spread = Math.max(maxWeight - minWeight, 1);
  const ratio = (weight - minWeight) / spread;
  const eased = Math.sqrt(Math.max(0, Math.min(1, ratio)));
  return Math.round(minSize + eased * (maxSize - minSize));
}

function pickSlot(slots: Slot[], keyword: DisplayKeyword, sortedIndex: number, usedSlots: Set<number>): Slot {
  if (sortedIndex < Math.min(12, slots.length) && !usedSlots.has(sortedIndex)) {
    usedSlots.add(sortedIndex);
    return slots[sortedIndex];
  }

  const start = (textHash(keyword.text) + sortedIndex * 7) % slots.length;
  for (let offset = 0; offset < slots.length; offset += 1) {
    const candidate = (start + offset) % slots.length;
    if (!usedSlots.has(candidate)) {
      usedSlots.add(candidate);
      return slots[candidate];
    }
  }

  return slots[start];
}

function positionKeywords(
  keywords: DisplayKeyword[],
  slots: Slot[],
  limit: number,
  minSize: number,
  maxSize: number,
  rotateSteps: number[]
): PositionedKeyword[] {
  const sorted = sortKeywords(keywords, limit);
  if (!sorted.length) {
    return [];
  }

  const weights = sorted.map((keyword) => keyword.weight);
  const minWeight = Math.min(...weights);
  const maxWeight = Math.max(...weights);
  const usedSlots = new Set<number>();

  return sorted.map((keyword, index) => {
    const hash = textHash(`${keyword.text}:${keyword.category ?? "neutral"}`);
    const slot = pickSlot(slots, keyword, index, usedSlots);
    const fontSize = scaleFontSize(keyword.weight, minWeight, maxWeight, minSize, maxSize);
    const opacity = Math.max(0.62, Math.min(1, 0.74 + (fontSize - minSize) / Math.max(maxSize - minSize, 1) * 0.26));

    return {
      text: keyword.text,
      weight: keyword.weight,
      category: keyword.category,
      left: slot.left,
      top: slot.top,
      fontSize,
      rotate: rotateSteps[hash % rotateSteps.length],
      opacity,
      colorVariant: hash % 5,
    };
  });
}

export function layoutCanopyKeywords(keywords: DisplayKeyword[]): PositionedKeyword[] {
  return positionKeywords(keywords, CANOPY_SLOTS, CANOPY_LIMIT, 16, 86, [-6, -3, 0, 0, 2, 4, 7]);
}

export function layoutTrunkKeywords(keywords: DisplayKeyword[]): PositionedKeyword[] {
  return positionKeywords(keywords, TRUNK_SLOTS, TRUNK_LIMIT, 12, 42, [-90, -8, -4, 0, 0, 5, 9, 90]);
}
