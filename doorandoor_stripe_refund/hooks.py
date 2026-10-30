def ensure_administration_channel(env):
    channel_name = env["ir.config_parameter"].sudo().get_param(
        "doorandoor_stripe_refund.admin_channel_name", "Administrators"
    )
    Channel = env["discuss.channel"].sudo()
    channel = Channel.search(
        [("name", "=", channel_name), ("channel_type", "=", "channel")],
        limit=1,
    )
    system_group = env.ref("base.group_system")
    manager_group = env.ref("doorandoor_control_cobros.group_ddc_manager")
    if not channel:
        channel = Channel.create(
            {
                "name": channel_name,
                "channel_type": "channel",
                "group_ids": [(6, 0, (system_group | manager_group).ids)],
            }
        )
    users = (system_group.users | manager_group.users).filtered(
        lambda user: user.active and not user.share
    )
    channel._add_members(users=users.sudo(), post_joined_message=False)
    return channel


def post_init_hook(env):
    ensure_administration_channel(env)

