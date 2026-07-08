// Global store: just the staff session for now. The guest split flow keeps
// its own local component state (guests aren't logged in).
import { getStoredUser } from "./services/api";

export const initialStore = () => ({
  user: getStoredUser(),
});

export default function storeReducer(store, action = {}) {
  switch (action.type) {
    case "set_user":
      return { ...store, user: action.payload || null };
    case "logout":
      return { ...store, user: null };
    default:
      console.warn("Unknown action type:", action.type);
      return store;
  }
}
