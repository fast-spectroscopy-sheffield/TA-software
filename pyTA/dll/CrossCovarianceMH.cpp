#include "pch.h"
#include <stdlib.h>
#include "CrossCovarianceMH.h"

void cross_cov(int size_a, int size_b, int nsamples, double matrix_a[1000000], double matrix_b[1000000], double matrix_c[100000]) {

    // Initialization of matrices which hold the mean of each row
    double* matrix_a_mean = (double*) malloc(size_a * sizeof(double));
    double* matrix_b_mean = (double*) malloc(size_b * sizeof(double));

    // Faster to compute division once
    double inv1 = (double)1 / nsamples;
    double inv2 = (double)1 / (nsamples - 1);

    // Cycling and variables
    double help_variable;
    int i;
    int j;
    int k;

    // Computes the mean of each row in matrix_a
    for (i = 0; i < size_a; i++) {
        help_variable = 0.0;
        for (j = 0; j < nsamples; j++) {
            help_variable += matrix_a[i * nsamples + j];
        }
        matrix_a_mean[i] = help_variable * inv1;
    }

    // Computes the mean of each row in matrix_b
    for (i = 0; i < size_b; i++) {
        help_variable = 0.0;
        for (j = 0; j < nsamples; j++) {
            help_variable += matrix_b[i * nsamples + j];
        }
        matrix_b_mean[i] = help_variable * inv1;
    }

    // Computes the dot product and saves it in an array which follows row-reading of an mxl matrix
    // where m and l are the pixel sizes of matrix_b and matrix_a, respectively
    #pragma omp parallel for private(j, k, help_variable) schedule(static)
    for (i = 0; i < size_b; i++) {
        for (j = 0; j < size_a; j++) {
            help_variable = 0.0;
            for (k = 0; k < nsamples; k++) {
                help_variable += (matrix_a[j * nsamples + k] - matrix_a_mean[j]) * (matrix_b[i * nsamples + k] - matrix_b_mean[i]);
            }
            matrix_c[i * size_a + j] = help_variable * inv2;
        }
    }

    // Free memory of the mean value matrices
    free(matrix_a_mean);
    free(matrix_b_mean);
}
