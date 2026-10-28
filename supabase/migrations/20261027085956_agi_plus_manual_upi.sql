create table public.agi_plus_settings (
 id text primary key check (id='agi_plus'), enabled boolean not null default false,
 checkout_enabled boolean not null default false, upi_id text not null default '', payee_name text not null default '',
 amount_paise integer not null default 19900 check(amount_paise=19900), duration_days integer not null default 30 check(duration_days=30),
 updated_at timestamptz not null default now()
);
insert into public.agi_plus_settings(id) values('agi_plus');
create table public.agi_plus_payments (
 id uuid primary key default gen_random_uuid(), user_id uuid references auth.users(id) on delete set null,
 customer_email text not null, submitted_reference text not null check(submitted_reference ~ '^[A-Z0-9]{10,40}$'),
 amount_paise integer not null default 19900 check(amount_paise=19900), currency text not null default 'INR' check(currency='INR'),
 status text not null default 'pending' check(status in ('pending','approved','rejected')),
 verified_reference text, created_at timestamptz not null default now(), reviewed_at timestamptz,
 reviewed_by uuid, review_note text, access_starts_at timestamptz, access_expires_at timestamptz,
 unique(user_id,submitted_reference), check(status <> 'approved' or (verified_reference ~ '^[A-Z0-9]{10,40}$' and reviewed_at is not null and reviewed_by is not null))
);
create unique index agi_plus_verified_reference_unique on public.agi_plus_payments(verified_reference) where verified_reference is not null;
create index agi_plus_payment_queue on public.agi_plus_payments(status,created_at desc);
create index agi_plus_payment_owner on public.agi_plus_payments(user_id,created_at desc);
create table public.agi_plus_memberships (
 user_id uuid primary key references auth.users(id) on delete cascade,
 starts_at timestamptz not null, expires_at timestamptz not null, revoked_at timestamptz,
 updated_at timestamptz not null default now(), check(expires_at>starts_at)
);
create table public.agi_plus_audit (
 id uuid primary key default gen_random_uuid(), payment_id uuid references public.agi_plus_payments(id),
 actor_id uuid not null, action text not null, note text not null, created_at timestamptz not null default now()
);
alter table public.agi_plus_settings enable row level security;
alter table public.agi_plus_payments enable row level security;
alter table public.agi_plus_memberships enable row level security;
alter table public.agi_plus_audit enable row level security;
revoke all on public.agi_plus_settings, public.agi_plus_payments, public.agi_plus_memberships, public.agi_plus_audit from public, anon, authenticated;
grant select,insert,update,delete on public.agi_plus_settings, public.agi_plus_payments, public.agi_plus_memberships, public.agi_plus_audit to service_role;
create function public.agi_plus_review_payment(payment_uuid uuid, actor_uuid uuid, decision text, bank_reference text, note text)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare p public.agi_plus_payments%rowtype; m public.agi_plus_memberships%rowtype; start_time timestamptz; end_time timestamptz;
begin
 if actor_uuid is null or decision not in ('approve','reject') or length(trim(coalesce(note,'')))<5 then raise exception 'Review details are required'; end if;
 select * into p from public.agi_plus_payments where id=payment_uuid for update;
 if not found then raise exception 'Payment not found'; end if;
 if p.status='approved' and decision='approve' then return jsonb_build_object('status','approved','expires_at',p.access_expires_at,'already_reviewed',true); end if;
 if p.status<>'pending' then raise exception 'Payment already reviewed'; end if;
 if decision='reject' then
  update public.agi_plus_payments set status='rejected',reviewed_at=now(),reviewed_by=actor_uuid,review_note=trim(note) where id=payment_uuid;
 else
  if p.user_id is null or p.amount_paise<>19900 or p.currency<>'INR' or bank_reference !~ '^[A-Z0-9]{10,40}$' or bank_reference is null then raise exception 'Verified bank credit details required'; end if;
  -- Lock each member row as well as the payment: parallel renewals cannot lose time.
  perform pg_advisory_xact_lock(hashtextextended(p.user_id::text,0));
  select * into m from public.agi_plus_memberships where user_id=p.user_id for update;
  start_time=now();
  end_time=greatest(now(),case when m.revoked_at is null then m.expires_at else now() end)+interval '30 days';
  insert into public.agi_plus_memberships(user_id,starts_at,expires_at,revoked_at) values(p.user_id,start_time,end_time,null)
  on conflict(user_id) do update set starts_at=case when public.agi_plus_memberships.expires_at>now() and public.agi_plus_memberships.revoked_at is null then public.agi_plus_memberships.starts_at else excluded.starts_at end,expires_at=excluded.expires_at,revoked_at=null,updated_at=now();
  update public.agi_plus_payments set status='approved',verified_reference=bank_reference,reviewed_at=now(),reviewed_by=actor_uuid,review_note=trim(note),access_starts_at=start_time,access_expires_at=end_time where id=payment_uuid;
 end if;
 insert into public.agi_plus_audit(payment_id,actor_id,action,note) values(payment_uuid,actor_uuid,decision,trim(note));
 return jsonb_build_object('status',case when decision='approve' then 'approved' else 'rejected' end,'expires_at',end_time,'already_reviewed',false);
end; $$;
revoke all on function public.agi_plus_review_payment(uuid,uuid,text,text,text) from public,anon,authenticated;
grant execute on function public.agi_plus_review_payment(uuid,uuid,text,text,text) to service_role;
