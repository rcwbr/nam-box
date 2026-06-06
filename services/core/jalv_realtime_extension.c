/*
 * jalv_realtime_extension.c - Real-time property control extension for jalv
 *
 * Add this to jalv to enable external control of property parameters (like NAM's model path)
 * without restarting or using state files.
 *
 * Build with: gcc -shared -fPIC -o libjalv_ext.so jalv_realtime_extension.c -lpthread
 * Run with: LD_PRELOAD=./libjalv_ext.so jalv PLUGIN_URI
 */

#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "jalv_internal.h"
#include "lv2/atom/forge.h"
#include "lv2/patch/patch.h"

// FIFO path for model control commands
#define MODEL_FIFO_PATH "/var/nam/model_change.fifo"

// Global state for FIFO
static int model_fifo_fd = -1;
static pthread_t monitor_thread;
static bool monitor_running = false;

// Function pointer types for jalv internals we need
typedef ControlID* (*jalv_control_by_symbol_fn)(Jalv* jalv, const char* sym);
typedef void (*jalv_set_control_fn)(Jalv* jalv, const ControlID* control,
                                    uint32_t size, LV2_URID type, const void* body);

// Pointers to jalv functions (resolved at runtime)
static jalv_control_by_symbol_fn real_jalv_control_by_symbol = NULL;
static jalv_set_control_fn real_jalv_set_control = NULL;


// Initialize FIFO and start monitor thread
static void init_model_control(void)
{
    // Create FIFO directory if needed
    mkdir("/var/nam", 0777);

    // Create FIFO if it doesn't exist
    if (access(MODEL_FIFO_PATH, F_OK) != 0) {
        mkfifo(MODEL_FIFO_PATH, 0666);
    }

    // Open FIFO non-blocking (will block on read until jalv tries to open)
    model_fifo_fd = open(MODEL_FIFO_PATH, O_RDONLY | O_NONBLOCK);

    // Resolve jalv function pointers
    // real_jalv_control_by_symbol = dlsym(RTLD_NEXT, "jalv_control_by_symbol");
    // real_jalv_set_control = dlsym(RTLD_NEXT, "jalv_set_control");
}


// Send a patch:Set message for the model property
static void send_model_change(Jalv* jalv, const char* path)
{
    // Get the model control by symbol
    ControlID* control = jalv_control_by_symbol(jalv, "model");

    if (!control) {
        fprintf(stderr, "model control not found\n");
        return;
    }

    if (control->type != PROPERTY) {
        fprintf(stderr, "model is not a property control\n");
        return;
    }

    // Size includes null terminator
    size_t path_len = strlen(path) + 1;

    // Send the patch:Set message via jalv's internal path
    jalv_set_control(jalv, control, path_len, jalv->urids.atom_Path, path);
}


// Modified jalv_update that checks for model changes
// This function is called by jalv's main loop each cycle
// To use: Add a call to check_model_fifo(jalv) at the start of jalv_update()
int jalv_update_with_model_check(Jalv* jalv)
{
    // Check for model change request from FIFO
    if (model_fifo_fd >= 0) {
        char path[1024] = {0};
        ssize_t n = read(model_fifo_fd, path, sizeof(path) - 1);

        if (n > 0) {
            path[n] = '\0';

            // Strip any trailing newline
            char* nl = strchr(path, '\n');
            if (nl) *nl = '\0';

            // Send to plugin
            send_model_change(jalv, path);

            // Reopen FIFO (reading from FIFO is destructive)
            close(model_fifo_fd);
            model_fifo_fd = open(MODEL_FIFO_PATH, O_RDONLY | O_NONBLOCK);
        }
    }

    // Call original jalv_update logic here
    // This is a simplified version - real implementation would hook more
    return jalv_update(jalv);
}


// Hook into jalv's main function (for LD_PRELOAD)
// Note: This is a simplified example - real implementation needs care
__attribute__((constructor))
static void jalv_realtime_ext_init(void)
{
    fprintf(stderr, "jalv realtime extension loaded\n");
    init_model_control();
}


__attribute__((destructor))
static void jalv_realtime_ext_fini(void)
{
    if (model_fifo_fd >= 0) {
        close(model_fifo_fd);
    }
    fprintf(stderr, "jalv realtime extension unloaded\n");
}


/*
 * Alternative: Direct modification to jalv.c
 *
 * Add this to the top of jalv_update() in jalv.c:
 *
 * static void check_model_fifo(Jalv* jalv) {
 *     static int fd = -1;
 *     static char path[1024] = {0};
 *
 *     if (fd < 0) {
 *         fd = open("/var/nam/model_change.fifo", O_RDONLY | O_NONBLOCK);
 *         if (fd < 0 && mkfifo("/var/nam/model_change.fifo", 0666) == 0) {
 *             fd = open("/var/nam/model_change.fifo", O_RDONLY | O_NONBLOCK);
 *         }
 *         if (fd < 0) return;
 *     }
 *
 *     ssize_t n = read(fd, path, sizeof(path) - 1);
 *     if (n > 0) {
 *         path[n] = '\0';
 *         char* nl = strchr(path, '\n');
 *         if (nl) *nl = '\0';
 *
 *         ControlID* control = jalv_control_by_symbol(jalv, "model");
 *         if (control && control->type == PROPERTY) {
 *             jalv_set_control(jalv, control, strlen(path) + 1,
 *                            jalv->urids.atom_Path, path);
 *         }
 *     }
 * }
 */