"use client";

import {
  ArrowUp,
  Bot,
  ChefHat,
  Clock3,
  Loader2,
  MapPin,
  MessageSquareText,
  Sparkles,
  Star,
  Utensils,
} from "lucide-react";
import { FormEvent, KeyboardEvent, useMemo, useRef, useState } from "react";
import {
  ChatMessage,
  Recommendation,
  sendChatMessage,
} from "@/lib/chat";

type ConversationItem = {
  message: ChatMessage;
  recommendations?: Recommendation[];
};

const initialMessage: ConversationItem = {
  message: {
    id: "welcome",
    role: "assistant",
    createdAt: new Date().toISOString(),
    content:
      "Tell me about restaurant visits, cravings, dietary restrictions, social posts, or the kind of meal you want. I will turn it into a recommendation-style response.",
  },
};

const promptChips = [
  "Visited Green Bowl 8 times, vegan and gluten-free",
  "I want a date-night restaurant under $$$",
  "My posts mention sushi, ramen, and tasting menus",
];

const flattenMessages = (items: ConversationItem[]) =>
  items.map((item) => item.message);

export default function Home() {
  const [items, setItems] = useState<ConversationItem[]>([initialMessage]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const recommendationCount = useMemo(
    () =>
      items.reduce(
        (total, item) => total + (item.recommendations?.length ?? 0),
        0,
      ),
    [items],
  );

  async function handleSubmit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();

    const trimmed = input.trim();
    if (!trimmed || isSending) {
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      createdAt: new Date().toISOString(),
    };

    setInput("");
    setError("");
    setIsSending(true);
    setItems((current) => [...current, { message: userMessage }]);

    try {
      const response = await sendChatMessage(trimmed, [
        ...flattenMessages(items),
        userMessage,
      ]);

      setItems((current) => [
        ...current,
        {
          message: response.message,
          recommendations: response.recommendations,
        },
      ]);
    } catch {
      setError("The mock assistant could not respond. Try again.");
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSubmit();
    }
  }

  return (
    <main className="min-h-screen bg-[#f6f3ee] text-[#1d1b18]">
      <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="hidden border-r border-[#ded6ca] bg-[#fffaf2] px-5 py-6 lg:flex lg:flex-col">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#26312b] text-white">
              <Utensils size={20} aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold">Food Agent UI</p>
              <p className="text-xs text-[#766f65]">Mocked LLM contract</p>
            </div>
          </div>

          <div className="mt-8 space-y-3">
            <div className="rounded-lg border border-[#e2d9cd] bg-white p-4">
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-[#887660]">
                Session
              </p>
              <p className="mt-3 text-2xl font-semibold">{items.length}</p>
              <p className="mt-1 text-sm text-[#766f65]">messages exchanged</p>
            </div>
            <div className="rounded-lg border border-[#e2d9cd] bg-white p-4">
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-[#887660]">
                Output
              </p>
              <p className="mt-3 text-2xl font-semibold">
                {recommendationCount}
              </p>
              <p className="mt-1 text-sm text-[#766f65]">
                recommendation cards
              </p>
            </div>
          </div>

          <div className="mt-auto rounded-lg border border-[#e2d9cd] bg-[#f8efe3] p-4">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Sparkles size={16} aria-hidden="true" />
              Phase one
            </div>
            <p className="mt-2 text-sm leading-6 text-[#625b51]">
              UI only. Express and the Python workflow can plug into this
              response contract later.
            </p>
          </div>
        </aside>

        <section className="flex min-h-screen flex-col">
          <header className="border-b border-[#ded6ca] bg-[#fffaf2]/85 px-4 py-4 backdrop-blur sm:px-6">
            <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="flex items-center gap-2 text-sm font-medium text-[#766f65]">
                  <Bot size={16} aria-hidden="true" />
                  Recommendation assistant
                </p>
                <h1 className="mt-1 text-xl font-semibold sm:text-2xl">
                  Interactive food discovery chat
                </h1>
              </div>
              <div className="hidden rounded-full border border-[#d6cabb] bg-white px-3 py-1.5 text-sm text-[#625b51] sm:block">
                Mock mode
              </div>
            </div>
          </header>

          <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
            <div className="mx-auto flex max-w-5xl flex-col gap-5">
              {items.map((item) => (
                <MessageBubble key={item.message.id} item={item} />
              ))}

              {isSending ? (
                <div className="flex max-w-3xl items-center gap-3 rounded-lg border border-[#ded6ca] bg-white px-4 py-3 text-sm text-[#625b51]">
                  <Loader2
                    className="animate-spin"
                    size={18}
                    aria-hidden="true"
                  />
                  The mock agent is reading your preference signals...
                </div>
              ) : null}

              {error ? (
                <div className="rounded-lg border border-[#e7b5a8] bg-[#fff2ee] px-4 py-3 text-sm text-[#8a2f20]">
                  {error}
                </div>
              ) : null}
            </div>
          </div>

          <div className="border-t border-[#ded6ca] bg-[#fffaf2] px-4 py-4 sm:px-6">
            <div className="mx-auto max-w-5xl">
              <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
                {promptChips.map((prompt) => (
                  <button
                    className="shrink-0 rounded-full border border-[#d6cabb] bg-white px-3 py-2 text-sm text-[#4c463e] transition hover:border-[#6d7f5f] hover:text-[#26312b] disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={isSending}
                    key={prompt}
                    onClick={() => {
                      setInput(prompt);
                      inputRef.current?.focus();
                    }}
                    type="button"
                  >
                    {prompt}
                  </button>
                ))}
              </div>

              <form
                className="flex items-end gap-3 rounded-lg border border-[#cabda8] bg-white p-2 shadow-sm"
                onSubmit={handleSubmit}
              >
                <textarea
                  aria-label="Message"
                  className="max-h-36 min-h-12 flex-1 resize-none bg-transparent px-3 py-3 text-sm leading-6 outline-none placeholder:text-[#9a9388]"
                  disabled={isSending}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Describe visits, cravings, dietary restrictions, social posts..."
                  ref={inputRef}
                  rows={1}
                  value={input}
                />
                <button
                  aria-label="Send message"
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-[#26312b] text-white transition hover:bg-[#38483d] disabled:cursor-not-allowed disabled:bg-[#b8afa3]"
                  disabled={!input.trim() || isSending}
                  title="Send message"
                  type="submit"
                >
                  {isSending ? (
                    <Loader2
                      className="animate-spin"
                      size={18}
                      aria-hidden="true"
                    />
                  ) : (
                    <ArrowUp size={19} aria-hidden="true" />
                  )}
                </button>
              </form>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function MessageBubble({ item }: { item: ConversationItem }) {
  const isUser = item.message.role === "user";

  return (
    <article
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
      aria-label={`${isUser ? "User" : "Assistant"} message`}
    >
      <div
        className={`max-w-3xl rounded-lg px-4 py-3 shadow-sm ${
          isUser
            ? "bg-[#26312b] text-white"
            : "border border-[#ded6ca] bg-white text-[#24211d]"
        }`}
      >
        <div className="mb-2 flex items-center gap-2 text-xs font-medium opacity-80">
          {isUser ? (
            <MessageSquareText size={14} aria-hidden="true" />
          ) : (
            <Bot size={14} aria-hidden="true" />
          )}
          {isUser ? "You" : "Assistant"}
        </div>
        <p className="whitespace-pre-wrap text-sm leading-6">
          {item.message.content}
        </p>

        {item.recommendations?.length ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {item.recommendations.map((recommendation) => (
              <RecommendationCard
                key={`${recommendation.kind}-${recommendation.name}`}
                recommendation={recommendation}
              />
            ))}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function RecommendationCard({
  recommendation,
}: {
  recommendation: Recommendation;
}) {
  const metadata = recommendation.metadata;

  return (
    <div className="rounded-lg border border-[#e4dacd] bg-[#fffaf2] p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-[#887660]">
            {recommendation.kind}
          </p>
          <h2 className="mt-1 text-base font-semibold leading-6">
            {recommendation.name}
          </h2>
        </div>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#e7f0df] text-[#344f32]">
          {recommendation.kind === "restaurant" ? (
            <MapPin size={17} aria-hidden="true" />
          ) : (
            <ChefHat size={17} aria-hidden="true" />
          )}
        </div>
      </div>

      <p className="mt-3 text-sm leading-6 text-[#5d554b]">
        {recommendation.reasoning}
      </p>

      <div className="mt-4 flex flex-wrap gap-2 text-xs text-[#4f493f]">
        {metadata?.cuisine ? (
          <span className="rounded-full bg-white px-2.5 py-1">
            {metadata.cuisine}
          </span>
        ) : null}
        {metadata?.price ? (
          <span className="rounded-full bg-white px-2.5 py-1">
            {metadata.price}
          </span>
        ) : null}
        {metadata?.rating ? (
          <span className="flex items-center gap-1 rounded-full bg-white px-2.5 py-1">
            <Star size={12} aria-hidden="true" />
            {metadata.rating.toFixed(1)}
          </span>
        ) : null}
        {metadata?.difficulty ? (
          <span className="rounded-full bg-white px-2.5 py-1">
            {metadata.difficulty}
          </span>
        ) : null}
        {metadata?.prepTime ? (
          <span className="flex items-center gap-1 rounded-full bg-white px-2.5 py-1">
            <Clock3 size={12} aria-hidden="true" />
            {metadata.prepTime}
          </span>
        ) : null}
      </div>
    </div>
  );
}
