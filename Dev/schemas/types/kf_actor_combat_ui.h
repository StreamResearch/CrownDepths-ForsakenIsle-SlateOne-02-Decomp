#pragma once
#include "primitives_and_sdk.h"

typedef enum KfEntityKind {
    KF_ENTITY_MONSTER = 1,
    KF_ENTITY_NPC = 3,
    KF_ENTITY_STATIC = 4,
    KF_ENTITY_NONE = 0xff
} KfEntityKind;

/* Monster / NPC archetype table at 0x80172624 (40 entries, stride 0x78) */
typedef struct KfEntityDef {
    u8 sub_type; /* +0x00 */
    u8 behavior_flags[8]; /* +0x01 */
    u8 aggro_type; /* +0x09 */
    u8 drop_item_id; /* +0x0a */
    u8 pad_0b[7]; /* +0x0b */
    s16 base_hp; /* +0x12 */
    s16 hitbox_radius; /* +0x14 */
    s16 sound_group; /* +0x16 */
    u16 walk_anim_id; /* +0x18 */
    u16 base_scale; /* +0x1a */
    s16 idle_anim_id; /* +0x1c */
    u8 pad_1e[20]; /* +0x1e */
    s16 tint_level; /* +0x32 */
    u32 flags; /* +0x34 */
    void *script_ptr; /* +0x38 */
    u8 pad_3c[60]; /* +0x3c */
} KfEntityDef; /* 0x78 */

/* Active world entity slot at 0x8016c544 (200 slots, stride 0x7c) */
typedef struct KfEntityState {
    u8 kind; /* +0x00 */
    u8 sub_type; /* +0x01 */
    u8 def_id; /* +0x02 */
    u8 spawn_flags; /* +0x03 */
    u8 state_timer; /* +0x04 */
    u8 move_flags; /* +0x05 */
    u8 layer; /* +0x06 */
    u8 tile_z; /* +0x07 */
    u8 tile_x; /* +0x08 */
    u8 active_state; /* +0x09 */
    u8 anim_phase; /* +0x0a */
    u8 aggro_flags; /* +0x0b */
    u8 anim_mode; /* +0x0c */
    u8 pad_0d; /* +0x0d */
    u8 ai_phase; /* +0x0e */
    u8 target_flag; /* +0x0f */
    s16 hp; /* +0x10 */
    u8 pad_12[8]; /* +0x12 */
    s16 idle_scale; /* +0x1a */
    s16 hitbox_radius; /* +0x1c */
    s16 sound_group; /* +0x1e */
    s16 home_dir; /* +0x20 */
    s16 spawn_z_off; /* +0x22 */
    s16 spawn_x_off; /* +0x24 */
    s16 spawn_y_off; /* +0x26 */
    u32 behavior_flags; /* +0x28 */
    s32 pos_x; /* +0x2c */
    s32 pos_y; /* +0x30 */
    s32 pos_z; /* +0x34 */
    u8 pad_38[8]; /* +0x38 */
    s16 rot_x; /* +0x40 */
    u16 rot_y; /* +0x42 */
    s16 rot_z; /* +0x44 */
    u16 pad_46; /* +0x46 */
    s16 scale_x; /* +0x48 */
    s16 scale_y; /* +0x4a */
    s16 scale_z; /* +0x4c */
    u16 pad_4e; /* +0x4e */
    u32 ai_aux[3]; /* +0x50 */
    void *model_handle; /* +0x5c */
    u8 pad_60[28]; /* +0x60 */
} KfEntityState; /* 0x7c */

/* Full 352-byte player progression, combat, equip & kinematics state at 0x80199414 */
typedef struct KfPlayerState {
    u32 experience; /* +0x00 */
    s32 next_level_xp; /* +0x04 */
    u8 level; /* +0x08 */
    u8 active_slot; /* +0x09 */
    u8 state_dirty; /* +0x0a */
    u8 weapon_charge_delay; /* +0x0b */
    u8 pad_0c; /* +0x0c */
    u8 cast_anim_state; /* +0x0d */
    u16 hit_flash_timer; /* +0x0e */
    u16 scale_or_light; /* +0x10 */
    s16 max_hp; /* +0x12 */
    s16 cur_hp; /* +0x14 */
    s16 max_mp; /* +0x16 */
    s16 cur_mp; /* +0x18 */
    u16 slash_stamina; /* +0x1a */
    u16 swing_or_charge_aux; /* +0x1c */
    u16 magic_stamina; /* +0x1e */
    s16 str_mod; /* +0x20 */
    s16 mag_mod; /* +0x22 */
    s16 base_strength; /* +0x24 */
    s16 base_magic; /* +0x26 */
    s16 eff_strength; /* +0x28 */
    s16 eff_magic; /* +0x2a */
    u32 gold; /* +0x2c */
    u16 atk_stats[8]; /* +0x30 */
    u16 pad_40; /* +0x40 */
    s16 def_stats[9]; /* +0x42 */
    s16 status_timers[14]; /* +0x54 */
    u32 pad_70; /* +0x70 */
    u32 elapsed_frames; /* +0x74 */
    void *equipped_spell_ptr; /* +0x78 */
    u32 active_fx_timer; /* +0x7c */
    void *equipped_weapon_ptr; /* +0x80 */
    void *weapon_anim_ptr; /* +0x84 */
    s32 weapon_swing_phase; /* +0x88 */
    s32 step_counter; /* +0x8c */
    u16 weapon_sound_id; /* +0x90 */
    u16 weapon_range; /* +0x92 */
    u16 weapon_hitbox_delay; /* +0x94 */
    u8 weapon_charge_flag; /* +0x96 */
    u8 equipped_magic_id; /* +0x97 */
    u8 equipped_item_id; /* +0x98 */
    u8 equipped_shield_id; /* +0x99 */
    u8 attack_dir; /* +0x9a */
    u8 equipped_weapon_id; /* +0x9b */
    u16 attack_cooldown; /* +0x9c */
    u8 weapon_two_handed; /* +0x9e */
    u8 compass_visible; /* +0x9f */
    u32 action_lock_flags; /* +0xa0 */
    void *equipped_item_ptrs[7]; /* +0xa4 */
    u8 equipped_equip_ids[7]; /* +0xc0 */
    u8 ui_hud_flags[7]; /* +0xc7 */
    u16 pad_ce; /* +0xce */
    u8 combat_flags[6]; /* +0xd0 */
    u16 pad_d6; /* +0xd6 */
    s32 pos_x; /* +0xd8 */
    s32 pos_y; /* +0xdc */
    s32 pos_z; /* +0xe0 */
    s32 standing_entity_id; /* +0xe4 */
    s16 grid_cell_x; /* +0xe8 */
    s16 floor_layer; /* +0xea */
    s32 grid_cell_z; /* +0xec */
    s32 view_angle_raw; /* +0xf0 */
    s32 look_pitch_vel; /* +0xf4 */
    s32 target_view_angles; /* +0xf8 */
    s32 target_look_pitch; /* +0xfc */
    s16 vel_x; /* +0x100 */
    s16 vel_y; /* +0x102 */
    s16 vel_z; /* +0x104 */
    s16 knockback_z; /* +0x106 */
    s16 move_accel_x; /* +0x108 */
    s16 move_accel_y; /* +0x10a */
    s32 move_accel_z; /* +0x10c */
    s16 turn_rate_yaw; /* +0x110 */
    s16 turn_rate_pitch; /* +0x112 */
    s32 turn_damping; /* +0x114 */
    s16 step_delta_x; /* +0x118 */
    s16 step_delta_y; /* +0x11a */
    s32 step_delta_z; /* +0x11c */
    s32 head_clearance; /* +0x120 */
    s32 upper_clearance; /* +0x124 */
    s16 time_hours; /* +0x128 */
    s16 walk_bob_phase; /* +0x12a */
    s16 walk_bob_amp; /* +0x12c */
    s16 footstep_timer; /* +0x12e */
    s16 fall_dist; /* +0x130 */
    s16 slope_pitch; /* +0x132 */
    s16 eye_height; /* +0x134 */
    s16 cam_roll; /* +0x136 */
    s16 eye_bob_y; /* +0x138 */
    s16 eye_tilt; /* +0x13a */
    s16 compass_angle; /* +0x13c */
    u16 compass_target; /* +0x13e */
    u16 pad_buttons_cur; /* +0x140 */
    u16 pad_buttons_edge; /* +0x142 */
    s32 analog_move_x; /* +0x144 */
    s32 analog_move_y; /* +0x148 */
    s8 ground_tile_type; /* +0x14c */
    u8 ground_step_mask; /* +0x14d */
    s16 ground_delta_y; /* +0x14e */
    s32 ground_height; /* +0x150 */
    s32 smooth_vel_x; /* +0x154 */
    s32 smooth_vel_z; /* +0x158 */
    s32 reserved_15c; /* +0x15c */
} KfPlayerState; /* 0x160 */
