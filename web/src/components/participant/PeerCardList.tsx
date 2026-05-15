import { Button } from "../common/Button";
import type { PublicCard } from "../../types/card";

type PeerCardListProps = {
  cards: PublicCard[];
  selectingId?: string;
  onSelect: (cardId: string) => void;
};

const PROMPT_LABELS: Record<string, string> = {
  to_past_me: "그때의 나에게",
  to_now_me: "지금의 나에게",
  to_colleague: "동료에게",
  stress_memory: "마음에 남은 상황"
};

export function PeerCardList({ cards, selectingId, onSelect }: PeerCardListProps) {
  return (
    <div className="peer-card-list">
      {cards.map((card) => (
        <article className="peer-card" key={card.id}>
          <p className="peer-card__eyebrow">{PROMPT_LABELS[card.promptType] ?? "마음카드"}</p>
          <p className="peer-card__content">{card.content}</p>
          <Button
            disabled={Boolean(selectingId)}
            fullWidth
            onClick={() => onSelect(card.id)}
            variant="secondary"
          >
            {selectingId === card.id ? "선택 중" : "이 카드 선택"}
          </Button>
        </article>
      ))}
    </div>
  );
}
