CREATE TABLE IF NOT EXISTS public.opted_out_users (
    user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, chat_id)
);

CREATE INDEX IF NOT EXISTS opted_out_users_chat_id_idx
ON public.opted_out_users (chat_id);
