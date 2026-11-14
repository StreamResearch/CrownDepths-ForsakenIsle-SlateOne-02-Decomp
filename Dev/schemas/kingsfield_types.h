#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "types/primitives_and_sdk.h"
#include "types/kf_containers_and_io.h"
#include "types/kf_world_and_render.h"
#include "types/kf_actor_combat_ui.h"

/* Function pointer callbacks (valid in C11; excluded from simple header regex parser) */
typedef void (*KfVoidCallback)(void);
typedef int32_t (*KfIntCallback)(int32_t);
