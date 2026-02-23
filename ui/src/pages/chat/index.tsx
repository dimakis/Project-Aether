import { ChatSidebar } from "./ChatSidebar";
import { ChatMessageList } from "./ChatMessageList";
import { ChatInput } from "./ChatInput";
import { ChatHeader } from "./ChatHeader";
import { useChatMessages } from "./hooks";

export function ChatPage() {
  const {
    sessions,
    activeSessionId,
    selectedModel,
    setSelectedModel,
    selectedAgent,
    setSelectedAgent,
    messages,
    startNewChat,
    switchSession,
    deleteSession,
    input,
    setInput,
    isStreaming,
    copiedIdx,
    statusMessage,
    elapsed,
    workflowSelection,
    setWorkflowSelection,
    sendMessage,
    handleCopyMessage,
    handleRetry,
    handleFeedback,
    handleCreateProposal,
    availableModels,
    recentConversations,
    activityPanelOpen,
  } = useChatMessages();

  return (
    <div className="flex h-full">
      <ChatSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        recentConversations={recentConversations}
        onNewChat={startNewChat}
        onSwitchSession={switchSession}
        onDeleteSession={deleteSession}
      />

      <div className="flex flex-1 overflow-hidden">
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <ChatHeader
            selectedModel={selectedModel}
            availableModels={availableModels}
            onModelChange={setSelectedModel}
            selectedAgent={selectedAgent}
            onAgentChange={setSelectedAgent}
            workflowSelection={workflowSelection}
            onWorkflowSelectionChange={setWorkflowSelection}
            isStreaming={isStreaming}
            statusMessage={statusMessage}
            elapsed={elapsed}
            activityPanelOpen={activityPanelOpen}
            onNewChat={startNewChat}
          />

          <ChatMessageList
            messages={messages}
            activeSessionId={activeSessionId}
            copiedIdx={copiedIdx}
            statusMessage={statusMessage}
            onCopy={handleCopyMessage}
            onRetry={handleRetry}
            onFeedback={handleFeedback}
            onCreateProposal={handleCreateProposal}
            onSuggestionClick={sendMessage}
          />

          <ChatInput
            value={input}
            onChange={setInput}
            onSend={() => sendMessage(input)}
            isStreaming={isStreaming}
          />
        </div>
      </div>
    </div>
  );
}

export default ChatPage;
