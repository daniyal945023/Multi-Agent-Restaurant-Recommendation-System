export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
};

export type Recommendation = {
  name: string;
  kind: "restaurant" | "recipe";
  reasoning: string;
  metadata?: {
    cuisine?: string;
    price?: string;
    rating?: number;
    difficulty?: string;
    prepTime?: string;
  };
};

export type ChatResponse = {
  message: ChatMessage;
  recommendations?: Recommendation[];
  workflowStep?:
    | "mocked"
    | "profile_generated"
    | "candidates_retrieved"
    | "complete";
};

const restaurantRecommendations: Recommendation[] = [
  {
    name: "Green Bowl",
    kind: "restaurant",
    reasoning:
      "A strong match for plant-forward meals with quick, familiar lunch options. It fits health-conscious preferences while keeping the experience casual and repeatable.",
    metadata: {
      cuisine: "Vegan bowls",
      price: "$$",
      rating: 4.6,
    },
  },
  {
    name: "Mediterranean Grill",
    kind: "restaurant",
    reasoning:
      "Mediterranean flavors line up well with fresh vegetables, herbs, legumes, and gluten-free friendly plates. It is a good pick when the user wants something bright but still filling.",
    metadata: {
      cuisine: "Mediterranean",
      price: "$$",
      rating: 4.4,
    },
  },
];

const recipeRecommendations: Recommendation[] = [
  {
    name: "Citrus Chickpea Power Bowl",
    kind: "recipe",
    reasoning:
      "This keeps the profile vegan and gluten-free while leaning into fresh, tangy flavors. It also works well for meal prep without feeling heavy.",
    metadata: {
      cuisine: "Mediterranean",
      difficulty: "Easy",
      prepTime: "25 min",
    },
  },
  {
    name: "Herbed Lentil Lettuce Wraps",
    kind: "recipe",
    reasoning:
      "A light, high-protein option with crunch, herbs, and a flexible sauce base. It is a good recommendation for users who like clean meals with enough texture.",
    metadata: {
      cuisine: "Modern healthy",
      difficulty: "Medium",
      prepTime: "35 min",
    },
  },
];

const sleep = (milliseconds: number) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

const createAssistantMessage = (content: string): ChatMessage => ({
  id: crypto.randomUUID(),
  role: "assistant",
  content,
  createdAt: new Date().toISOString(),
});

export async function sendChatMessage(
  input: string,
  history: ChatMessage[],
): Promise<ChatResponse> {
  await sleep(850);

  const normalizedInput = input.toLowerCase();
  const hasDietSignal =
    normalizedInput.includes("vegan") ||
    normalizedInput.includes("gluten") ||
    normalizedInput.includes("diet") ||
    normalizedInput.includes("allerg");

  const hasSocialSignal =
    normalizedInput.includes("post") ||
    normalizedInput.includes("instagram") ||
    normalizedInput.includes("social") ||
    normalizedInput.includes("visited");

  const opening =
    history.length > 2
      ? "I updated the recommendation read based on your latest message."
      : "I read this like a first-pass profile for the recommendation agents.";

  const focus = hasDietSignal
    ? "Dietary constraints are the priority, so I would bias retrieval toward clearly labeled vegan and gluten-free options before ranking taste fit."
    : hasSocialSignal
      ? "Your visit history and posts give useful behavioral signals, so I would use them to infer cuisine patterns, budget, and dining occasions."
      : "I would start by extracting cuisine preferences, budget hints, dietary needs, and the kind of dining mood you are describing.";

  return {
    message: createAssistantMessage(
      `${opening} ${focus} Here are mock recommendations using the same response shape the future Express endpoint can return.`,
    ),
    recommendations: [
      ...restaurantRecommendations,
      ...recipeRecommendations,
    ].slice(0, hasDietSignal ? 4 : 3),
    workflowStep: "mocked",
  };
}
