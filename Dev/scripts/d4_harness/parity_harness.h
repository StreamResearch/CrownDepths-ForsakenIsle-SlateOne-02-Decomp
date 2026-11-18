#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "kingsfield_types.h"
#include "kingsfield_globals.h"

/* Lifted C declarations under test from readable translation units */
extern s32 kf_game_math_step_linear_clamp(s32 cur_val, s32 target_val, s32 step_delta);
extern bool kf_game_math_is_angle_cw_halfplane(s32 angle_a, s32 angle_b);
extern s32 kf_game_math_angle_diff_signed(s32 angle_a, s32 angle_b);
extern bool kf_game_math_intervals_overlap(s32 pos_a, s32 neg_extent, s32 pos_b, s32 pos_extent);
extern s32 kf_game_math_lerp_q12(s32 start_val, s32 end_val, s32 t_q12);
extern u32 kf_game_math_lerp_angle_q12(s32 start_angle, s16 end_angle, s32 t_q12);
extern void kf_game_math_lerp_pose_s16(s16 *src_pose, s16 *dst_pose, s16 *out_pose, s16 t_q12);
extern s32 kf_game_cd_bcd_to_int(u32 bcd_byte);
extern u32 kf_game_cd_int_to_bcd(u32 value);
extern bool kf_game_cd_verify_sector_checksum(s32 *buf, s32 sector_count);
extern s32 kf_game_t_archive_get_entry_size(u32 archive_slot, u32 entry_idx);
extern void kf_game_player_clamp_mp_regen(void);
extern void kf_game_player_clamp_hp_regen(void);
extern s32 kf_game_mc_checksum_payload(u8 *payload);
extern s32 kf_game_player_scale_gauge(s32 stat_val, s32 divisor);
extern s32 kf_game_player_eval_combat_curve(s32 base_val, s32 bonus_val, s32 scale_step);
extern void kf_end_init_str_decoder_state(void);

typedef struct D4ParityResult {
    const char *name;
    int is_passed;
} D4ParityResult;

uint32_t d4_rd_le32(const uint8_t *p);
uint16_t d4_rd_le16(const uint8_t *p);
uint8_t *d4_read_file_alloc(const char *standalone_dir, const char *rel, size_t *out_size);
size_t d4_read_file_head(const char *standalone_dir, const char *rel, uint8_t *buf, size_t max_len);
int d4_run_abi_and_media_tests(const char *standalone_dir, D4ParityResult *out, int max_out);
int d4_run_gameplay_and_str_tests(D4ParityResult *out, int max_out);
