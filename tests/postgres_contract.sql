-- DISPOSABLE TEST DB ONLY. All fixture writes are rolled back.
-- Run setup.sql first; use an empty database (revision 0).
\set ON_ERROR_STOP on
begin;
do $$ begin
 if exists(select 1 from arriva_private.workspace) then raise exception 'Use an empty disposable database'; end if;
 if has_function_privilege('anon','public.arriva_rpc(text,jsonb)','EXECUTE') or has_function_privilege('authenticated','public.arriva_rpc(text,jsonb)','EXECUTE') then raise exception 'Unexpected public execution grant'; end if;
 if not has_function_privilege('service_role','public.arriva_rpc(text,jsonb)','EXECUTE') then raise exception 'Service role missing grant'; end if;
 if has_schema_privilege('service_role','arriva_private','USAGE') then raise exception 'Direct schema access granted'; end if;
end $$;
set local role service_role;
do $$
declare r jsonb; i int;
begin
 r:=public.arriva_rpc('load'); if r->'state' is distinct from 'null'::jsonb then raise exception 'Initial state not null'; end if;
 r:=public.arriva_rpc('save','{"expected":0,"state":{"revision":1,"tasks":["test"]}}'); if not (r->>'ok')::bool then raise exception 'Save failed %',r;end if;
 r:=public.arriva_rpc('load'); if r->'state'->>'revision'<>'1' then raise exception 'Load mismatch';end if;
 r:=public.arriva_rpc('save','{"expected":0,"state":{"revision":1}}'); if r->>'code' is distinct from 'stale' then raise exception 'Stale not rejected';end if;
 r:=public.arriva_rpc('proposal_create','{"expected":1,"token_hash":"hash-a","proposal":{"revision":1,"kind":"task"}}'); if not (r->>'ok')::bool then raise exception 'Proposal failed';end if;
 r:=public.arriva_rpc('proposal_get','{"token_hash":"hash-a"}'); if not (r->>'ok')::bool then raise exception 'Proposal missing';end if;
 r:=public.arriva_rpc('confirm','{"expected":1,"token_hash":"hash-a","state":{"revision":2,"tasks":["test","confirmed"]}}'); if not (r->>'ok')::bool then raise exception 'Confirm failed %',r;end if;
 r:=public.arriva_rpc('proposal_get','{"token_hash":"hash-a"}'); if r->>'code' is distinct from 'expired' then raise exception 'Replay possible';end if;
 r:=public.arriva_rpc('proposal_create','{"expected":2,"token_hash":"hash-b","proposal":{"revision":2,"kind":"task"}}');
 r:=public.arriva_rpc('proposal_decline','{"token_hash":"hash-b"}');
 r:=public.arriva_rpc('confirm','{"expected":2,"token_hash":"hash-b","state":{"revision":3}}'); if r->>'code' is distinct from 'expired' then raise exception 'Decline failed';end if;
 r:=public.arriva_rpc('proposal_create','{"expected":2,"token_hash":"hash-c","proposal":{"revision":2,"kind":"task"}}');
 r:=public.arriva_rpc('save','{"expected":2,"state":{"revision":3}}');
 r:=public.arriva_rpc('confirm','{"expected":3,"token_hash":"hash-c","state":{"revision":4}}'); if r->>'code' is distinct from 'stale' then raise exception 'Stale proposal failed';end if;
 for i in 1..12 loop r:=public.arriva_rpc('rate','{"bucket":"ai"}');if not (r->>'ok')::bool then raise exception 'Early throttle';end if;end loop;
 r:=public.arriva_rpc('rate','{"bucket":"ai"}');if r->>'code' is distinct from 'limit' then raise exception 'No throttle';end if;
 r:=public.arriva_rpc('lease_acquire','{"token_hash":"lease-a"}');if not (r->>'ok')::bool then raise exception 'Lease failed';end if;
 r:=public.arriva_rpc('lease_acquire','{"token_hash":"lease-b"}');if not (r->>'ok')::bool then raise exception 'Lease failed';end if;
 r:=public.arriva_rpc('lease_acquire','{"token_hash":"lease-c"}');if r->>'code' is distinct from 'busy' then raise exception 'Concurrency limit failed';end if;
 r:=public.arriva_rpc('lease_release','{"token_hash":"lease-a"}');r:=public.arriva_rpc('lease_acquire','{"token_hash":"lease-c"}');if not (r->>'ok')::bool then raise exception 'Lease release failed';end if;
 raise notice 'PASS: real PostgreSQL RPC, permission, revision, proposal and distributed limits contract';
end $$;
rollback;
