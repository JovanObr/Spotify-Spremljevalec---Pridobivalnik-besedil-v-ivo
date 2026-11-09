import { useQueryClient } from "@tanstack/react-query";

import { api } from "../api/client";

/** Logs out of Spotify and returns to the connect screen. */
export function useDisconnect() {
  const queryClient = useQueryClient();

  return async () => {
    await api.logout();
    queryClient.clear();
    await queryClient.invalidateQueries({ queryKey: ["status"] });
  };
}
