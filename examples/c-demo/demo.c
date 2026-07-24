#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum result {
    RESULT_OK = 0,
    RESULT_INVALID = 2,
    RESULT_TOO_LONG = 3
};

static int validate_input(const char *input)
{
    if (input == NULL || input[0] == '\0') {
        return RESULT_INVALID;
    }
    if (strlen(input) > 32U) {
        return RESULT_TOO_LONG;
    }
    return RESULT_OK;
}

static unsigned checksum(const char *input)
{
    unsigned value = 0U;
    for (size_t index = 0U; input[index] != '\0'; ++index) {
        if (input[index] >= 'a' && input[index] <= 'z') {
            value += (unsigned)(input[index] - 'a' + 1);
        } else {
            value += (unsigned)(unsigned char)input[index];
        }
    }
    return value;
}

static void safe_sink(unsigned value)
{
    printf("checksum=%u\n", value);
}

static void unsafe_sink(const char *value)
{
    /* Deliberately unsafe but harmless: demonstrates an unsanitized source-to-sink path. */
    printf("raw=%s\n", value);
}

static int process_request(const char *input, int unsafe_mode)
{
    int status = validate_input(input);
    if (status != RESULT_OK) {
        fprintf(stderr, "validation failed: %d\n", status);
        return status;
    }

    unsigned value = checksum(input);
    if (unsafe_mode != 0) {
        unsafe_sink(input);
    } else {
        safe_sink(value);
    }
    return RESULT_OK;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s VALUE [--unsafe]\n", argv[0]);
        return EXIT_FAILURE;
    }
    int unsafe_mode = argc > 2 && strcmp(argv[2], "--unsafe") == 0;
    return process_request(argv[1], unsafe_mode);
}
