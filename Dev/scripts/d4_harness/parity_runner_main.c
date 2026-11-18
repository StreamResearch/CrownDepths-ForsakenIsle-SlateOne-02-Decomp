/* Clean-room D4 host LP32 parity helpers and Standard 18 JSON test runner. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "parity_harness.h"

uint32_t d4_rd_le32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

uint16_t d4_rd_le16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

uint8_t *d4_read_file_alloc(const char *standalone_dir, const char *rel, size_t *out_size) {
    char path[1024];
    snprintf(path, sizeof(path), "%s/disc/files/%s", standalone_dir, rel);
    FILE *fp = fopen(path, "rb");
    if (!fp) return NULL;
    if (fseek(fp, 0, SEEK_END) != 0) { fclose(fp); return NULL; }
    long sz = ftell(fp);
    if (sz < 0 || fseek(fp, 0, SEEK_SET) != 0) { fclose(fp); return NULL; }
    uint8_t *buf = (uint8_t *)malloc((size_t)sz);
    if (!buf) { fclose(fp); return NULL; }
    size_t got = fread(buf, 1, (size_t)sz, fp);
    fclose(fp);
    if (got != (size_t)sz) { free(buf); return NULL; }
    if (out_size) *out_size = (size_t)sz;
    return buf;
}

size_t d4_read_file_head(const char *standalone_dir, const char *rel, uint8_t *buf, size_t max_len) {
    char path[1024];
    snprintf(path, sizeof(path), "%s/disc/files/%s", standalone_dir, rel);
    FILE *fp = fopen(path, "rb");
    if (!fp) return 0;
    size_t got = fread(buf, 1, max_len, fp);
    fclose(fp);
    return got;
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    const char *standalone_dir = "standalone";
    for (int i = 1; i + 1 < argc; ++i) {
        if (strcmp(argv[i], "--standalone-dir") == 0) standalone_dir = argv[i + 1];
    }

    D4ParityResult results[16];
    int total = 0;
    total += d4_run_abi_and_media_tests(standalone_dir, results + total, 16 - total);
    total += d4_run_gameplay_and_str_tests(results + total, 16 - total);

    int passed = 0;
    for (int i = 0; i < total; ++i) passed += results[i].is_passed ? 1 : 0;
    printf(
        "{\"assertionsPassedCount\": %d, \"assertionsTotalCount\": %d, \"isPassed\": %s, \"tests\": [",
        passed, total, (total > 0 && passed == total) ? "true" : "false"
    );
    for (int i = 0; i < total; ++i) {
        printf(
            "%s{\"name\": \"%s\", \"isPassed\": %s}",
            i ? ", " : "", results[i].name, results[i].is_passed ? "true" : "false"
        );
    }
    printf("]}\n");
    return (total > 0 && passed == total) ? 0 : 1;
}
