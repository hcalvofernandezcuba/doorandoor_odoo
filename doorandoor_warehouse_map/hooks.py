def post_init_hook(env):
    env["doorandoor.warehouse.map.position"]._sync_from_existing_batches()
