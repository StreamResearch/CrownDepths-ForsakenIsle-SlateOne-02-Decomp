#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* LP32 (pointer_bytes=4) PS1 R3000A primitives & Ghidra aliases */
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef int8_t s8;
typedef int16_t s16;
typedef int32_t s32;
typedef int64_t s64;
typedef float f32;
typedef double f64;
typedef int32_t bool32;
typedef u8 byte;
typedef u16 ushort;
typedef u32 uint;
typedef u32 ulong;
typedef u8 undefined;
typedef u8 undefined1;
typedef u16 undefined2;
typedef u32 undefined4;
typedef u64 undefined8;
#ifndef GHIDRA_COMPAT_FIXED_INTS
typedef int32_t code;
#endif

/* PS1 GPU primitives & environments */
typedef struct RECT {
    s16 x; /* +0x00 */
    s16 y; /* +0x02 */
    s16 w; /* +0x04 */
    s16 h; /* +0x06 */
} RECT; /* 0x08 */

typedef struct DISPENV {
    RECT disp; /* +0x00 */
    RECT screen; /* +0x08 */
    u8 isinter; /* +0x10 */
    u8 isrgb24; /* +0x11 */
    u8 pad0; /* +0x12 */
    u8 pad1; /* +0x13 */
} DISPENV; /* 0x14 */

typedef struct DR_ENV {
    u32 tag; /* +0x00 */
    u32 code[15]; /* +0x04 */
} DR_ENV; /* 0x40 */

typedef struct DRAWENV {
    RECT clip; /* +0x00 */
    s16 ofs[2]; /* +0x08 */
    RECT tw; /* +0x0c */
    u16 tpage; /* +0x14 */
    u8 dtd; /* +0x16 */
    u8 dfe; /* +0x17 */
    u8 isbg; /* +0x18 */
    u8 r0; /* +0x19 */
    u8 g0; /* +0x1a */
    u8 b0; /* +0x1b */
    DR_ENV dr_env; /* +0x1c */
} DRAWENV; /* 0x5c */

typedef struct DR_AREA {
    u32 tag; /* +0x00 */
    u32 code[2]; /* +0x04 */
} DR_AREA; /* 0x0c */

typedef struct DR_LOAD {
    u32 tag; /* +0x00 */
    u32 code[3]; /* +0x04 */
    u32 p[13]; /* +0x10 */
} DR_LOAD; /* 0x44 */

typedef struct DR_OFFSET {
    u32 tag; /* +0x00 */
    u32 code[2]; /* +0x04 */
} DR_OFFSET; /* 0x0c */

typedef struct GsF_LIGHT {
    s32 vx; /* +0x00 */
    s32 vy; /* +0x04 */
    s32 vz; /* +0x08 */
    u8 r; /* +0x0c */
    u8 g; /* +0x0d */
    u8 b; /* +0x0e */
    u8 pad; /* +0x0f */
} GsF_LIGHT; /* 0x10 */

typedef struct GsOT {
    u32 length; /* +0x00 */
    u32 *org; /* +0x04 */
    u32 offset; /* +0x08 */
    u32 point; /* +0x0c */
    u32 *tag; /* +0x10 */
} GsOT; /* 0x14 */

/* PS1 GTE fixed-point math & geometry */
typedef struct MATRIX {
    s16 m[3][3]; /* +0x00 */
    u16 pad; /* +0x12 */
    s32 t[3]; /* +0x14 */
} MATRIX; /* 0x20 */

typedef struct VECTOR {
    s32 vx; /* +0x00 */
    s32 vy; /* +0x04 */
    s32 vz; /* +0x08 */
    s32 pad; /* +0x0c */
} VECTOR; /* 0x10 */

typedef struct SVECTOR {
    s16 vx; /* +0x00 */
    s16 vy; /* +0x02 */
    s16 vz; /* +0x04 */
    s16 pad; /* +0x06 */
} SVECTOR; /* 0x08 */

typedef struct CVECTOR {
    u8 r; /* +0x00 */
    u8 g; /* +0x01 */
    u8 b; /* +0x02 */
    u8 cd; /* +0x03 */
} CVECTOR; /* 0x04 */

typedef struct DVECTOR {
    s16 vx; /* +0x00 */
    s16 vy; /* +0x02 */
} DVECTOR; /* 0x04 */

/* PS1 CD-ROM, Memory Card & Kernel BIOS structs */
typedef struct CdlLOC {
    u8 minute; /* +0x00 */
    u8 second; /* +0x01 */
    u8 sector; /* +0x02 */
    u8 track; /* +0x03 */
} CdlLOC; /* 0x04 */

typedef struct CdlFILTER {
    u8 file; /* +0x00 */
    u8 chan; /* +0x01 */
    u16 pad; /* +0x02 */
} CdlFILTER; /* 0x04 */

typedef struct CdlFILE {
    CdlLOC pos; /* +0x00 */
    u32 size; /* +0x04 */
    char name[16]; /* +0x08 */
} CdlFILE; /* 0x18 */

typedef struct DIRENTRY {
    char name[20]; /* +0x00 */
    s32 attr; /* +0x14 */
    s32 size; /* +0x18 */
    struct DIRENTRY *next; /* +0x1c */
    s32 head; /* +0x20 */
    char system[4]; /* +0x24 */
} DIRENTRY; /* 0x28 */

typedef struct EXEC {
    u32 pc0; /* +0x00 */
    u32 gp0; /* +0x04 */
    u32 t_addr; /* +0x08 */
    u32 t_size; /* +0x0c */
    u32 d_addr; /* +0x10 */
    u32 d_size; /* +0x14 */
    u32 b_addr; /* +0x18 */
    u32 b_size; /* +0x1c */
    u32 s_addr; /* +0x20 */
    u32 s_size; /* +0x24 */
    u32 sp; /* +0x28 */
    u32 fp; /* +0x2c */
    u32 gp; /* +0x30 */
    u32 ret; /* +0x34 */
    u32 base; /* +0x38 */
} EXEC; /* 0x3c */

/* PS1 SPU / Sound structs */
typedef struct SpuVolume {
    s16 left; /* +0x00 */
    s16 right; /* +0x02 */
} SpuVolume; /* 0x04 */

typedef struct SpuExtAttr {
    SpuVolume volume; /* +0x00 */
    s32 reverb; /* +0x04 */
    s32 mix; /* +0x08 */
} SpuExtAttr; /* 0x0c */

typedef struct SpuCommonAttr {
    u32 mask; /* +0x00 */
    SpuVolume mvol; /* +0x04 */
    SpuVolume mvolmode; /* +0x08 */
    SpuExtAttr cd; /* +0x0c */
    SpuExtAttr ext; /* +0x18 */
} SpuCommonAttr; /* 0x24 */

typedef struct SpuVoiceAttr {
    u32 voice; /* +0x00 */
    u32 mask; /* +0x04 */
    SpuVolume volume; /* +0x08 */
    SpuVolume volmode; /* +0x0c */
    SpuVolume volumex; /* +0x10 */
    u16 pitch; /* +0x14 */
    u16 note; /* +0x16 */
    u16 sample_note; /* +0x18 */
    s16 envx; /* +0x1a */
    u32 addr; /* +0x1c */
    u32 loop_addr; /* +0x20 */
    s32 a_mode; /* +0x24 */
    s32 s_mode; /* +0x28 */
    s32 r_mode; /* +0x2c */
    u16 ar; /* +0x30 */
    u16 dr; /* +0x32 */
    u16 sr; /* +0x34 */
    u16 rr; /* +0x36 */
    u16 sl; /* +0x38 */
    u16 adsr1; /* +0x3a */
    u16 adsr2; /* +0x3c */
    u16 pad; /* +0x3e */
} SpuVoiceAttr; /* 0x40 */

typedef struct SpuReverbDepth {
    s16 left; /* +0x00 */
    s16 right; /* +0x02 */
} SpuReverbDepth; /* 0x04 */

typedef struct SpuReverbAttr {
    u32 mask; /* +0x00 */
    s32 mode; /* +0x04 */
    SpuReverbDepth depth; /* +0x08 */
    s32 delay; /* +0x0c */
    s32 feedback; /* +0x10 */
} SpuReverbAttr; /* 0x14 */

typedef struct ProgAtr {
    u8 tones; /* +0x00 */
    u8 mvol; /* +0x01 */
    u8 prior; /* +0x02 */
    u8 mode; /* +0x03 */
    u8 mpan; /* +0x04 */
    s8 reserved0; /* +0x05 */
    s16 attr; /* +0x06 */
    u32 reserved1; /* +0x08 */
    u32 reserved2; /* +0x0c */
} ProgAtr; /* 0x10 */

typedef struct VagAtr {
    u8 prior; /* +0x00 */
    u8 mode; /* +0x01 */
    u8 vol; /* +0x02 */
    u8 pan; /* +0x03 */
    u8 center; /* +0x04 */
    u8 shift; /* +0x05 */
    u8 min; /* +0x06 */
    u8 max; /* +0x07 */
    u8 vibW; /* +0x08 */
    u8 vibT; /* +0x09 */
    u8 porW; /* +0x0a */
    u8 porT; /* +0x0b */
    u8 pbmin; /* +0x0c */
    u8 pbmax; /* +0x0d */
    u8 reserved1; /* +0x0e */
    u8 reserved2; /* +0x0f */
    u16 adsr1; /* +0x10 */
    u16 adsr2; /* +0x12 */
    s16 prog; /* +0x14 */
    s16 vag; /* +0x16 */
    s16 reserved[4]; /* +0x18 */
} VagAtr; /* 0x20 */
