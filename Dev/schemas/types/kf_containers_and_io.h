#pragma once
#include "primitives_and_sdk.h"

/* SLUS_001.58 boot overlay selector & .T container slots */
typedef enum KfExeSelector {
    KF_EXE_OPEN = 0,
    KF_EXE_GAME = 1,
    KF_EXE_END = 2
} KfExeSelector;

typedef enum KfTArchiveId {
    KF_T_MO = 0,
    KF_T_RTMD = 1,
    KF_T_RTIM = 2,
    KF_T_TALK = 3,
    KF_T_VAB = 4,
    KF_T_FDAT = 5,
    KF_T_ITEM = 6
} KfTArchiveId;

typedef struct KfTArchiveSlot {
    u16 *sector_offsets; /* +0x00 */
    CdlLOC start_loc; /* +0x04 */
    u32 total_size; /* +0x08 */
} KfTArchiveSlot; /* 0x0c */

typedef struct KfTArchiveHeader {
    u16 entry_count; /* +0x00 */
    u16 sector_offsets[1]; /* +0x02 */
} KfTArchiveHeader; /* 0x04 */

typedef struct KfFdatHeader {
    u32 section_size; /* +0x00 */
} KfFdatHeader; /* 0x04 */

typedef struct KfMoHeader {
    u32 total_size; /* +0x00 */
    u32 anim_count; /* +0x04 */
    u32 tmd_offset; /* +0x08 */
    u32 keyframe_table_offset; /* +0x0c */
    u32 anim_table_offset; /* +0x10 */
} KfMoHeader; /* 0x14 */

typedef struct KfRtimHeader {
    RECT src_rect; /* +0x00 */
    RECT dst_rect; /* +0x08 */
} KfRtimHeader; /* 0x10 */

/* Equipment / defense modifier table at 0x801d9a2c (stride 0x20) */
typedef struct KfItemDef {
    u8 category; /* +0x00 */
    u8 equip_slot; /* +0x01 */
    s16 pdef_bonus; /* +0x02 */
    s16 mdef_bonus; /* +0x04 */
    s16 slash_res; /* +0x06 */
    s16 chop_res; /* +0x08 */
    s16 stab_res; /* +0x0a */
    s16 fire_res; /* +0x0c */
    s16 earth_res; /* +0x0e */
    s16 wind_res; /* +0x10 */
    s16 water_res; /* +0x12 */
    s16 light_res; /* +0x14 */
    u16 flags; /* +0x16 */
    u32 price; /* +0x18 */
    u32 reserved; /* +0x1c */
} KfItemDef; /* 0x20 */

/* Weapon / spell attack definition table at 0x801c7fbc (stride 0x44) */
typedef struct KfMagicDef {
    u8 id; /* +0x00 */
    u8 two_handed; /* +0x01 */
    u8 spell_slot; /* +0x02 */
    u8 element_flags; /* +0x03 */
    u16 reserved_04; /* +0x04 */
    u16 atk_stats[8]; /* +0x06 */
    u8 anim_data[10]; /* +0x16 */
    u16 swing_speed; /* +0x20 */
    u16 attack_range; /* +0x22 */
    u8 extra[10]; /* +0x24 */
    u16 hitbox_delay; /* +0x2e */
    u16 mp_cost; /* +0x30 */
    u16 stamina_cost; /* +0x32 */
    u16 sound_id; /* +0x34 */
    u16 reserved_36; /* +0x36 */
    u16 cast_cost; /* +0x38 */
    u16 reserved_3a; /* +0x3a */
    u32 price; /* +0x3c */
    u32 reserved_40; /* +0x40 */
} KfMagicDef; /* 0x44 */

/* PS1 Memory Card BASLUS-00158 block header + checksum at +0x200 (payload starts at +0x400) */
typedef struct KfSaveHeader {
    char magic[2]; /* +0x00 */
    u8 icon_type; /* +0x02 */
    u8 block_count; /* +0x03 */
    char title_sjis[64]; /* +0x04 */
    u8 reserved_44[28]; /* +0x44 */
    u16 icon_clut[16]; /* +0x60 */
    u8 icon_frames[3][128]; /* +0x80 */
    s32 checksum; /* +0x200 */
    u8 reserved_204[508]; /* +0x204 */
} KfSaveHeader; /* 0x400 */
