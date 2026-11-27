-- ARRIVA Studio v4: run once in Supabase SQL Editor as project owner.
-- Idempotent; does not reset existing workspace. All writes serialized by an advisory transaction lock.
begin;
create schema if not exists arriva_private;
revoke all on schema arriva_private from public, anon, authenticated, service_role;
create table if not exists arriva_private.workspace (
 id smallint primary key check(id=1), revision bigint not null check(revision>=0), payload jsonb not null
);
create table if not exists arriva_private.proposals (
 token_hash text primary key, revision bigint not null, payload jsonb not null, expires_at timestamptz not null
);
create table if not exists arriva_private.request_events (
 bucket text not null, occurred_at timestamptz not null default clock_timestamp()
);
create index if not exists request_events_bucket_time on arriva_private.request_events(bucket, occurred_at);
create table if not exists arriva_private.ai_leases (
 token_hash text primary key, expires_at timestamptz not null
);
alter table arriva_private.workspace enable row level security;
alter table arriva_private.proposals enable row level security;
alter table arriva_private.request_events enable row level security;
alter table arriva_private.ai_leases enable row level security;
revoke all on all tables in schema arriva_private from public, anon, authenticated, service_role;
-- Security definer owned by the SQL Editor role; only the service role may invoke it.
create or replace function public.arriva_rpc(action text, input jsonb default '{}'::jsonb)
returns jsonb language plpgsql security definer set search_path = pg_catalog as $$
declare
 current_rev bigint;
 expected bigint;
 p arriva_private.proposals%rowtype;
 ts timestamptz;
 b text;
 cap integer;
 token text;
 result jsonb;
begin
 if action = 'load' then
  select payload into result from arriva_private.workspace where id=1;
  return jsonb_build_object('ok',true,'state',result);
 end if;
 perform pg_advisory_xact_lock(761426, 4101);
 ts := clock_timestamp();
 if action in ('save','confirm','proposal_create') then
  select revision into current_rev from arriva_private.workspace where id=1;
  current_rev := coalesce(current_rev,0);
  expected := (input->>'expected')::bigint;
  if expected is null or current_rev <> expected then
   return jsonb_build_object('ok',false,'code','stale');
  end if;
 end if;
 if action in ('save','confirm') then
  if jsonb_typeof(input->'state') is distinct from 'object' or (input->'state'->>'revision')::bigint is distinct from expected+1 then
   return jsonb_build_object('ok',false,'code','invalid');
  end if;
  if action = 'confirm' then
   select * into p from arriva_private.proposals where token_hash=input->>'token_hash';
   if not found or p.expires_at<=ts then return jsonb_build_object('ok',false,'code','expired'); end if;
   if p.revision<>current_rev then return jsonb_build_object('ok',false,'code','stale'); end if;
  end if;
  insert into arriva_private.workspace(id,revision,payload) values(1,expected+1,input->'state')
   on conflict(id) do update set revision=excluded.revision,payload=excluded.payload;
  if action='confirm' then delete from arriva_private.proposals where token_hash=input->>'token_hash'; end if;
  return jsonb_build_object('ok',true);
 elsif action='proposal_create' then
  delete from arriva_private.proposals where expires_at<=ts;
  if (select count(*) from arriva_private.proposals)>=200 then return jsonb_build_object('ok',false,'code','limit'); end if;
  insert into arriva_private.proposals(token_hash,revision,payload,expires_at)
   values(input->>'token_hash',expected,input->'proposal',ts+interval '15 minutes');
  return jsonb_build_object('ok',true,'expires_at',extract(epoch from ts+interval '15 minutes'));
 elsif action='proposal_get' then
  select * into p from arriva_private.proposals where token_hash=input->>'token_hash' and expires_at>ts;
  if not found then return jsonb_build_object('ok',false,'code','expired'); end if;
  return jsonb_build_object('ok',true,'proposal',p.payload || jsonb_build_object('expiry',extract(epoch from p.expires_at)));
 elsif action='proposal_decline' then
  delete from arriva_private.proposals where token_hash=input->>'token_hash';
  return jsonb_build_object('ok',true);
 elsif action='rate' then
  b:=input->>'bucket'; cap:=case b when 'auth-failed' then 60 when 'read' then 180 when 'write' then 60 when 'ai' then 12 else 0 end;
  if cap=0 then return jsonb_build_object('ok',false,'code','invalid'); end if;
  delete from arriva_private.request_events where occurred_at<=ts-interval '60 seconds';
  if (select count(*) from arriva_private.request_events where bucket=b)>=cap then return jsonb_build_object('ok',false,'code','limit'); end if;
  insert into arriva_private.request_events(bucket,occurred_at) values(b,ts);
  return jsonb_build_object('ok',true);
 elsif action='lease_acquire' then
  delete from arriva_private.ai_leases where expires_at<=ts;
  if (select count(*) from arriva_private.ai_leases)>=2 then return jsonb_build_object('ok',false,'code','busy'); end if;
  insert into arriva_private.ai_leases(token_hash,expires_at) values(input->>'token_hash',ts+interval '330 seconds');
  return jsonb_build_object('ok',true);
 elsif action='lease_release' then
  delete from arriva_private.ai_leases where token_hash=input->>'token_hash';
  return jsonb_build_object('ok',true);
 end if;
 return jsonb_build_object('ok',false,'code','invalid');
end;
$$;
revoke all on function public.arriva_rpc(text,jsonb) from public, anon, authenticated, service_role;
grant execute on function public.arriva_rpc(text,jsonb) to service_role;
grant usage on schema public to service_role;
notify pgrst, 'reload schema';
commit;
