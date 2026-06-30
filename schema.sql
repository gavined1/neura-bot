create table if not exists conversations (
    id bigserial primary key,
    user_id bigint not null,
    group_id bigint not null,
    role text not null check (role in ('user', 'assistant')),
    message text not null,
    created_at timestamptz default now()
);

create index if not exists idx_conversations_user_group_created
    on conversations (user_id, group_id, created_at);
