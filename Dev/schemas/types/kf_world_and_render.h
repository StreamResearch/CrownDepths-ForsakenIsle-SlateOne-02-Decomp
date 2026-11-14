#pragma once
#include "primitives_and_sdk.h"

/* Double-buffered PS1 draw & display environments at 0x8018e0ac */
typedef struct KfGfxEnv {
    DRAWENV draw[2]; /* +0x00 */
    DISPENV disp[2]; /* +0xb8 */
} KfGfxEnv; /* 0xe0 */

/* Camera / GTE view state at 0x80192e78 */
typedef struct KfCameraState {
    s32 pos_x; /* +0x00 */
    s32 pos_y; /* +0x04 */
    s32 pos_z; /* +0x08 */
    s32 pos_w; /* +0x0c */
    s16 pitch; /* +0x10 */
    s16 yaw; /* +0x12 */
    s16 roll; /* +0x14 */
    s16 pad_angle; /* +0x16 */
    s32 cell_x; /* +0x18 */
    s32 cell_z; /* +0x1c */
    s32 grid_origin_x; /* +0x20 */
    s32 grid_origin_z; /* +0x24 */
    s32 inv_origin_x; /* +0x28 */
    s32 inv_origin_z; /* +0x2c */
    s32 fog_near; /* +0x30 */
} KfCameraState; /* 0x34 */

/* Scene / map loading state machine at 0x8017e05c */
typedef struct KfSceneControl {
    u16 state; /* +0x00 */
    u16 phase; /* +0x02 */
    u8 cur_map; /* +0x04 */
    u8 cur_bgm; /* +0x05 */
    u8 cur_vab; /* +0x06 */
    u8 cur_env; /* +0x07 */
    u8 cur_fade_mode; /* +0x08 */
    u8 sector_counter; /* +0x09 */
    u16 pad_0a; /* +0x0a */
    void *callbacks; /* +0x0c */
    u8 next_map; /* +0x10 */
    u8 next_bgm; /* +0x11 */
    u8 next_vab; /* +0x12 */
    u8 next_env; /* +0x13 */
    u8 next_fade_mode; /* +0x14 */
    u8 entry_x; /* +0x15 */
    u8 entry_z; /* +0x16 */
    u8 fade_r; /* +0x17 */
    u8 fade_g; /* +0x18 */
    u8 fade_b; /* +0x19 */
    s16 fade_timer; /* +0x1a */
} KfSceneControl; /* 0x1c */

/* 80x80 dual-layer tile map cell at 0x801c8484 (6400 cells = 64000 bytes) */
typedef struct KfMapCell {
    u8 lower_tile_id; /* +0x00 */
    u8 lower_elevation; /* +0x01 */
    u8 lower_tex_flags; /* +0x02 */
    u8 lower_collision; /* +0x03 */
    u8 lower_render_flags; /* +0x04 */
    u8 upper_tile_id; /* +0x05 */
    u8 upper_elevation; /* +0x06 */
    u8 upper_tex_flags; /* +0x07 */
    u8 upper_collision; /* +0x08 */
    u8 upper_render_flags; /* +0x09 */
} KfMapCell; /* 0x0a */

/* Map object archetype table at 0x80175914 (stride 0x18) */
typedef struct KfMapObjDef {
    u8 kind; /* +0x00 */
    u8 sub_kind; /* +0x01 */
    u8 sound_slot; /* +0x02 */
    u8 flags; /* +0x03 */
    s16 interact_radius; /* +0x04 */
    u16 script_id; /* +0x06 */
    u16 model_id; /* +0x08 */
    u16 trigger_flags; /* +0x0a */
    u16 anim_speed; /* +0x0c */
    u16 param_0e; /* +0x0e */
    u32 extra_0; /* +0x10 */
    u32 extra_1; /* +0x14 */
} KfMapObjDef; /* 0x18 */

/* Live interactive map object instance at 0x80177714 (396 slots, stride 0x44) */
typedef struct KfMapObjState {
    u8 layer; /* +0x00 */
    u8 alpha; /* +0x01 */
    u8 mode; /* +0x02 */
    u8 def_flags; /* +0x03 */
    u8 active_slot; /* +0x04 */
    u8 state; /* +0x05 */
    u16 def_id; /* +0x06 */
    u16 anim_timer; /* +0x08 */
    u16 phase; /* +0x0a */
    u16 model_id; /* +0x0c */
    u16 anim_frame; /* +0x0e */
    u16 reserved_10; /* +0x10 */
    u16 reserved_12; /* +0x12 */
    s32 pos_x; /* +0x14 */
    s32 pos_y; /* +0x18 */
    s32 pos_z; /* +0x1c */
    s32 model_handle; /* +0x20 */
    s16 rot_x; /* +0x24 */
    u16 rot_y; /* +0x26 */
    s16 rot_z; /* +0x28 */
    s16 scale_x; /* +0x2a */
    s16 scale_y; /* +0x2c */
    s16 scale_z; /* +0x2e */
    u32 model_cache; /* +0x30 */
    s16 vel_x; /* +0x34 */
    s16 vel_y; /* +0x36 */
    u32 script_arg0; /* +0x38 */
    u32 script_arg1; /* +0x3c */
    u8 flags[4]; /* +0x40 */
} KfMapObjState; /* 0x44 */

/* World drop / pickup slot at 0x80195174 (128 slots, stride 0x18) */
typedef struct KfWorldDrop {
    s16 item_id; /* +0x00 */
    u8 layer; /* +0x02 */
    u8 quantity; /* +0x03 */
    u8 owner_flags; /* +0x04 */
    u8 anim_phase; /* +0x05 */
    u16 pad_06; /* +0x06 */
    s32 pos_x; /* +0x08 */
    s32 pos_y; /* +0x0c */
    s32 pos_z; /* +0x10 */
    u32 reserved_14; /* +0x14 */
} KfWorldDrop; /* 0x18 */

/* Animated VRAM texture strip at 0x80192d58 (8 slots, stride 0x18) */
typedef struct KfTextureAnimSlot {
    u8 active; /* +0x00 */
    u8 interval; /* +0x01 */
    u8 timer; /* +0x02 */
    u8 step; /* +0x03 */
    s16 scroll_offset; /* +0x04 */
    s16 vram_x; /* +0x06 */
    s16 vram_y; /* +0x08 */
    s16 vram_w; /* +0x0a */
    s16 vram_h; /* +0x0c */
    u16 pad_0e; /* +0x0e */
    void *pixel_data; /* +0x10 */
    u32 reserved_14; /* +0x14 */
} KfTextureAnimSlot; /* 0x18 */
