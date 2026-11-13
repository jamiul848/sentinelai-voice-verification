import { create } from "zustand";

interface DemoState {
  isDemoMode: boolean;
  toggleDemoMode: () => void;
  setDemoMode: (val: boolean) => void;
}

export const useDemoStore = create<DemoState>((set) => ({
  isDemoMode: false,
  toggleDemoMode: () => set((state) => ({ isDemoMode: !state.isDemoMode })),
  setDemoMode: (val: boolean) => set({ isDemoMode: val }),
}));

