import type { DisplayKeyword } from "../types/display";

export type WordCloudRegion = "canopy" | "trunk";

export type WordCloudLayoutOptions = {
  region: WordCloudRegion;
  width: number;
  height: number;
  maxWords: number;
  minFontSize: number;
  maxFontSize: number;
  maxAttemptsPerWord: number;
  collisionMargin: number;
};

export type PositionedWord = {
  text: string;
  weight: number;
  category?: string | null;
  x: number;
  y: number;
  fontSize: number;
  rotate: number;
  opacity: number;
  colorVariant: number;
  width: number;
  height: number;
};

type Box = {
  x: number;
  y: number;
  width: number;
  height: number;
};

const CANOPY_OPTIONS: WordCloudLayoutOptions = {
  region: "canopy",
  width: 980,
  height: 520,
  maxWords: 60,
  minFontSize: 16,
  maxFontSize: 86,
  maxAttemptsPerWord: 120,
  collisionMargin: 1.05,
};

const TRUNK_OPTIONS: WordCloudLayoutOptions = {
  region: "trunk",
  width: 360,
  height: 360,
  maxWords: 28,
  minFontSize: 12,
  maxFontSize: 38,
  maxAttemptsPerWord: 120,
  collisionMargin: 0.9,
};

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function hashText(value: string): number {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function sortKeywords(keywords: DisplayKeyword[], maxWords: number): DisplayKeyword[] {
  return [...keywords]
    .sort((left, right) => {
      if (right.weight !== left.weight) {
        return right.weight - left.weight;
      }
      return left.text.localeCompare(right.text, "ko-KR");
    })
    .slice(0, maxWords);
}

function getWeightRatio(weight: number, minWeight: number, maxWeight: number): number {
  const spread = maxWeight - minWeight;
  if (spread <= 0) {
    return 0.55;
  }
  return clamp((weight - minWeight) / spread, 0, 1);
}

function scaleFontSize(
  weight: number,
  minWeight: number,
  maxWeight: number,
  minSize: number,
  maxSize: number
): number {
  const ratio = getWeightRatio(weight, minWeight, maxWeight);
  const eased = Math.pow(ratio, 0.55);
  return Math.round(minSize + eased * (maxSize - minSize));
}

function ellipse(x: number, y: number, cx: number, cy: number, rx: number, ry: number): boolean {
  const dx = (x - cx) / rx;
  const dy = (y - cy) / ry;
  return dx * dx + dy * dy <= 1;
}

function isInsideCanopy(x: number, y: number): boolean {
  return (
    ellipse(x, y, 50, 48, 42, 30) ||
    ellipse(x, y, 33, 52, 28, 24) ||
    ellipse(x, y, 67, 52, 28, 24)
  );
}

function isInsideTrunk(x: number, y: number): boolean {
  if (y < 6 || y > 98) {
    return false;
  }
  const progress = (y - 6) / 92;
  const widthAtY = 12 + progress * 26;
  return Math.abs(x - 50) <= widthAtY / 2;
}

function isInsideRegion(region: WordCloudRegion, x: number, y: number): boolean {
  if (x < 0 || x > 100 || y < 0 || y > 100) {
    return false;
  }
  return region === "canopy" ? isInsideCanopy(x, y) : isInsideTrunk(x, y);
}

function estimateTextBox(
  text: string,
  fontSize: number,
  rotate: number,
  regionWidthPx: number,
  regionHeightPx: number
): { width: number; height: number } {
  const characterCount = Array.from(text).length;
  const hangulCharWidth = fontSize * 0.9;
  const widthPx = Math.max(fontSize * 1.8, characterCount * hangulCharWidth);
  const heightPx = fontSize * 1.18;
  const rotationPadding = Math.abs(rotate) > 0 ? 1.08 : 1;

  return {
    width: (widthPx * rotationPadding / regionWidthPx) * 100,
    height: (heightPx * rotationPadding / regionHeightPx) * 100,
  };
}

function collides(left: Box, right: Box, margin: number): boolean {
  return !(
    left.x + left.width / 2 + margin < right.x - right.width / 2 ||
    left.x - left.width / 2 - margin > right.x + right.width / 2 ||
    left.y + left.height / 2 + margin < right.y - right.height / 2 ||
    left.y - left.height / 2 - margin > right.y + right.height / 2
  );
}

function canPlaceBox(region: WordCloudRegion, box: Box, placedBoxes: Box[], margin: number): boolean {
  return boxInsideRegion(region, box) && !placedBoxes.some((placedBox) => collides(box, placedBox, margin));
}

function boxInsideRegion(region: WordCloudRegion, box: Box): boolean {
  if (
    box.x - box.width / 2 < 0 ||
    box.x + box.width / 2 > 100 ||
    box.y - box.height / 2 < 0 ||
    box.y + box.height / 2 > 100
  ) {
    return false;
  }

  if (region === "trunk") {
    return (
      isInsideRegion(region, box.x, box.y) &&
      isInsideRegion(region, box.x - box.width / 2, box.y) &&
      isInsideRegion(region, box.x + box.width / 2, box.y) &&
      isInsideRegion(region, box.x, box.y - box.height / 2) &&
      isInsideRegion(region, box.x, box.y + box.height / 2)
    );
  }

  return (
    isInsideRegion(region, box.x, box.y) &&
    isInsideRegion(region, box.x - box.width / 2, box.y - box.height / 2) &&
    isInsideRegion(region, box.x + box.width / 2, box.y - box.height / 2) &&
    isInsideRegion(region, box.x - box.width / 2, box.y + box.height / 2) &&
    isInsideRegion(region, box.x + box.width / 2, box.y + box.height / 2)
  );
}

function getCandidatePosition(
  region: WordCloudRegion,
  wordIndex: number,
  attempt: number,
  hash: number
): { x: number; y: number } {
  const hashAngleOffset = ((hash % 360) * Math.PI) / 180;
  const angle = attempt * 0.58 + hashAngleOffset;

  if (region === "trunk") {
    const baseY = 14 + ((attempt * 5.5 + wordIndex * 11) % 82);
    const xOffset = Math.sin(angle) * Math.min(18, attempt * 0.45);
    return {
      x: 50 + xOffset,
      y: baseY,
    };
  }

  const spiralRadius = attempt * 0.75;
  return {
    x: 50 + Math.cos(angle) * spiralRadius * 1.35,
    y: 48 + Math.sin(angle) * spiralRadius * 0.78,
  };
}

function pickRotation(region: WordCloudRegion, wordIndex: number, hash: number): number {
  if (wordIndex < 5) {
    const topRotations = region === "canopy" ? [-3, 0, 3] : [-5, 0, 5];
    return topRotations[hash % topRotations.length];
  }

  const rotations = region === "canopy" ? [-6, -3, 0, 0, 0, 3, 6] : [-10, -5, 0, 0, 5, 10];
  return rotations[hash % rotations.length];
}

function fontShrinkFactor(attempt: number): number {
  if (attempt >= 80) {
    return 0.86;
  }
  if (attempt >= 40) {
    return 0.92;
  }
  return 1;
}

function getFallbackCandidates(region: WordCloudRegion, hash: number): Array<{ x: number; y: number }> {
  const canopyCandidates = [
    { x: 50, y: 48 },
    { x: 41, y: 44 },
    { x: 59, y: 44 },
    { x: 36, y: 56 },
    { x: 64, y: 56 },
    { x: 50, y: 62 },
  ];
  const trunkCandidates = [
    { x: 50, y: 20 },
    { x: 50, y: 38 },
    { x: 50, y: 56 },
    { x: 47, y: 74 },
    { x: 53, y: 84 },
  ];
  const candidates = region === "canopy" ? canopyCandidates : trunkCandidates;
  const offset = hash % candidates.length;
  return candidates.map((_, index) => candidates[(index + offset) % candidates.length]);
}

function placeWord(
  keyword: DisplayKeyword,
  index: number,
  options: WordCloudLayoutOptions,
  minWeight: number,
  maxWeight: number,
  placedBoxes: Box[]
): PositionedWord | null {
  const hash = hashText(`${keyword.text}:${keyword.category ?? "neutral"}`);
  const baseFontSize = scaleFontSize(
    keyword.weight,
    minWeight,
    maxWeight,
    options.minFontSize,
    options.maxFontSize
  );
  const rotate = pickRotation(options.region, index, hash);
  const ratio = getWeightRatio(keyword.weight, minWeight, maxWeight);

  for (let attempt = 0; attempt < options.maxAttemptsPerWord; attempt += 1) {
    const fontSize = Math.round(baseFontSize * fontShrinkFactor(attempt));
    if (fontSize < options.minFontSize) {
      return null;
    }

    const position = getCandidatePosition(options.region, index, attempt, hash);
    const size = estimateTextBox(keyword.text, fontSize, rotate, options.width, options.height);
    const candidateBox: Box = {
      x: position.x,
      y: position.y,
      width: size.width,
      height: size.height,
    };

    if (!canPlaceBox(options.region, candidateBox, placedBoxes, options.collisionMargin)) {
      continue;
    }

    placedBoxes.push(candidateBox);
    return {
      text: keyword.text,
      weight: keyword.weight,
      category: keyword.category,
      x: Number(position.x.toFixed(2)),
      y: Number(position.y.toFixed(2)),
      fontSize,
      rotate,
      opacity: clamp(0.7 + ratio * 0.24 + ((hash % 7) - 3) * 0.01, 0.64, 1),
      colorVariant: hash % 5,
      width: Number(size.width.toFixed(2)),
      height: Number(size.height.toFixed(2)),
    };
  }

  if (index < 5) {
    const fallbackRotate = 0;
    const fallbackFontSize = Math.max(options.minFontSize, Math.round(baseFontSize * 0.74));
    const fallbackSize = estimateTextBox(
      keyword.text,
      fallbackFontSize,
      fallbackRotate,
      options.width,
      options.height
    );

    for (const position of getFallbackCandidates(options.region, hash)) {
      const fallbackBox: Box = {
        x: position.x,
        y: position.y,
        width: fallbackSize.width,
        height: fallbackSize.height,
      };
      if (!canPlaceBox(options.region, fallbackBox, placedBoxes, options.collisionMargin * 0.7)) {
        continue;
      }

      placedBoxes.push(fallbackBox);
      return {
        text: keyword.text,
        weight: keyword.weight,
        category: keyword.category,
        x: position.x,
        y: position.y,
        fontSize: fallbackFontSize,
        rotate: fallbackRotate,
        opacity: clamp(0.7 + ratio * 0.24, 0.64, 1),
        colorVariant: hash % 5,
        width: Number(fallbackSize.width.toFixed(2)),
        height: Number(fallbackSize.height.toFixed(2)),
      };
    }
  }

  return null;
}

export function layoutWordCloud(
  keywords: DisplayKeyword[],
  options: WordCloudLayoutOptions
): PositionedWord[] {
  const sorted = sortKeywords(keywords, options.maxWords);
  if (!sorted.length) {
    return [];
  }

  const weights = sorted.map((keyword) => keyword.weight);
  const minWeight = Math.min(...weights);
  const maxWeight = Math.max(...weights);
  const placedBoxes: Box[] = [];
  const positionedWords: PositionedWord[] = [];

  sorted.forEach((keyword, index) => {
    const positioned = placeWord(keyword, index, options, minWeight, maxWeight, placedBoxes);
    if (positioned) {
      positionedWords.push(positioned);
    }
  });

  return positionedWords;
}

export function layoutCanopyKeywords(keywords: DisplayKeyword[]): PositionedWord[] {
  return layoutWordCloud(keywords, CANOPY_OPTIONS);
}

export function layoutTrunkKeywords(keywords: DisplayKeyword[]): PositionedWord[] {
  return layoutWordCloud(keywords, TRUNK_OPTIONS);
}
