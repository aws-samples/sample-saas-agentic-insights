import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useState, useEffect, useRef } from "react";
import { MessageSquare } from "lucide-react";
import { Message, MessageContent } from "@/components/ai-elements/message";
import {
  Tool,
  ToolHeader,
  ToolContent,
  ToolInput,
  ToolOutput,
} from "@/components/ai-elements/tool";
import { Response } from "@/components/ai-elements/response";
import { Badge } from "@/components/ui/badge";
import {
  PromptInput,
  PromptInputTextarea,
  PromptInputSubmit,
} from "@/components/ai-elements/prompt-input";

export default function ChurnAnalysis() {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({
      api: `https://bedrock-agentcore.${
        import.meta.env.VITE_REGION
      }.amazonaws.com/runtimes/${encodeURIComponent(
        import.meta.env.VITE_CHURN_AGENT_ARN
      )}/invocations?qualifier=DEFAULT`,
      headers: {
        Authorization: `Bearer ${localStorage.getItem("adminToken") || ""}`,
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": crypto.randomUUID(),
      },
    }),
  });

  // Auto-scroll to bottom when messages change or status changes
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, status]);

  const handleSubmit = (message: any) => {
    if (!message.text?.trim()) return;
    sendMessage(message);
    setInput(""); // Clear input after submit
  };

  // Type guard for tool- prefixed parts
  const isToolPart = (part: any): part is { type: `tool-${string}` } => {
    return typeof part.type === "string" && part.type.startsWith("tool-");
  };

  const renderMessage = (message: (typeof messages)[0]) => {
    return (
      <Message key={message.id} from={message.role}>
        <MessageContent className="prose">
          {message.parts.map((part, i) => {
            switch (part.type) {
              case "text":
                return <Response key={i}>{part.text}</Response>;
              case "reasoning":
                return <Response key={i}>{part.text}</Response>;
              case "dynamic-tool":
                return (
                  <Tool key={i} defaultOpen={true}>
                    <ToolHeader
                      type={`tool-${part.toolName}`}
                      state={part.state || "complete"}
                    />
                    <ToolContent>
                      <ToolInput input={part.input} />
                      {part.output !== undefined && (
                        <ToolOutput
                          output={
                            <Response>{JSON.stringify(part.output)}</Response>
                          }
                          errorText={part.errorText}
                        />
                      )}
                    </ToolContent>
                  </Tool>
                );
              default:
                if (isToolPart(part)) {
                  return (
                    <Tool key={i} defaultOpen={true}>
                      <ToolHeader type={part.type} state={part.state} />
                      <ToolContent>
                        <ToolInput input={part.input || {}} />
                        {!!part.output && (
                          <ToolOutput
                            output={
                              <Response>{JSON.stringify(part.output)}</Response>
                            }
                            errorText={part.errorText}
                          />
                        )}
                      </ToolContent>
                    </Tool>
                  );
                }
                return null;
            }
          })}
        </MessageContent>
      </Message>
    );
  };

  return (
    <div className="grid grid-rows-[auto_1fr_auto] h-[calc(100vh-4rem)] gap-4">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
          Churn Analysis
        </h1>
        <Badge
          variant={
            status === "ready"
              ? "default"
              : status === "streaming"
              ? "secondary"
              : "destructive"
          }
        >
          {status}
        </Badge>
      </div>

      <div ref={scrollRef} className="overflow-y-auto space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <MessageSquare className="size-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Start a conversation</h3>
            <p className="text-muted-foreground">
              Ask about churn patterns, retention strategies, or customer
              insights
            </p>
          </div>
        ) : (
          messages.map((message) => renderMessage(message))
        )}

        {false && status === "streaming" && (
          <Message from="assistant">
            <MessageContent>
              <div className="animate-pulse">Analyzing data...</div>
            </MessageContent>
          </Message>
        )}
      </div>

      <div className="border-t pt-4">
        <PromptInput
          onSubmit={handleSubmit}
          className="w-full max-w-2xl mx-auto relative"
        >
          <PromptInputTextarea
            value={input}
            placeholder="Ask about churn patterns, retention strategies, or customer insights..."
            onChange={(e) => setInput(e.currentTarget.value)}
            disabled={status === "streaming"}
            className="pr-12"
          />
          <PromptInputSubmit
            status={status === "streaming" ? "streaming" : "ready"}
            disabled={status !== "ready" || !input.trim()}
            className="absolute bottom-1 right-1"
          />
        </PromptInput>
      </div>
    </div>
  );
}
