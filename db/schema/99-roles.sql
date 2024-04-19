CREATE role anon;

grant all on database memory to anon;
grant all ON all functions IN SCHEMA public TO anon;
grant all ON all tables IN SCHEMA public TO anon;