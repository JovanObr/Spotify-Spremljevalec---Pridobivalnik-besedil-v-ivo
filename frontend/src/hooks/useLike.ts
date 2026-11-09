import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "../api/client";
import type { Track } from "../api/types";
import { strings } from "../lib/strings";
import { usePlayback } from "../playback/PlaybackProvider";
import { useIsLiked } from "./queries";

/** Liked state of a song plus a toggle that updates the heart instantly. */
export function useLike(track: Track | null | undefined) {
  const queryClient = useQueryClient();
  const { notify } = usePlayback();
  const uri = track?.uri ?? null;
  const { data: isLiked = false, isPending } = useIsLiked(uri);

  const mutation = useMutation({
    mutationFn: (liked: boolean) => api.setLiked([uri!], liked),
    onMutate: (liked) => {
      queryClient.setQueryData(["liked", uri], liked);
    },
    onSuccess: (_data, liked) => {
      notify(liked ? strings.like.liked(track!.title) : strings.like.unliked(track!.title));
      queryClient.invalidateQueries({ queryKey: ["liked-tracks"] });
    },
    onError: (_error, liked) => {
      queryClient.setQueryData(["liked", uri], !liked);
      notify(strings.like.failed);
    },
  });

  return {
    isLiked,
    isReady: Boolean(uri) && !isPending,
    toggle: () => uri && mutation.mutate(!isLiked),
  };
}
