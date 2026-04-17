import { create } from "zustand";
import type { Message, Contact } from "@/types";

interface Conversation {
  contact: Contact;
  lastMessage: Message | null;
  unreadCount: number;
  channel: "whatsapp" | "email" | "multi";
}

interface InboxState {
  conversations: Conversation[];
  activeConversationId: string | null;
  unreadTotal: number;
  setConversations: (conversations: Conversation[]) => void;
  setActiveConversation: (contactId: string | null) => void;
  incrementUnread: (contactId: string) => void;
  markRead: (contactId: string) => void;
}

export const useInboxStore = create<InboxState>((set) => ({
  conversations: [],
  activeConversationId: null,
  unreadTotal: 0,
  setConversations: (conversations) =>
    set({
      conversations,
      unreadTotal: conversations.reduce((sum, c) => sum + c.unreadCount, 0),
    }),
  setActiveConversation: (contactId) => set({ activeConversationId: contactId }),
  incrementUnread: (contactId) =>
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.contact.id === contactId ? { ...c, unreadCount: c.unreadCount + 1 } : c,
      ),
      unreadTotal: state.unreadTotal + 1,
    })),
  markRead: (contactId) =>
    set((state) => {
      const conv = state.conversations.find((c) => c.contact.id === contactId);
      const decrement = conv?.unreadCount || 0;
      return {
        conversations: state.conversations.map((c) =>
          c.contact.id === contactId ? { ...c, unreadCount: 0 } : c,
        ),
        unreadTotal: Math.max(0, state.unreadTotal - decrement),
      };
    }),
}));
