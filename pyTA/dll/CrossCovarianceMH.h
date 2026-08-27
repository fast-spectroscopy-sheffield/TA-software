// CrossCovarianceMH.h – Contains a cross covariance calculation
#pragma once

#ifdef CROSSCOVARIANCEMH_EXPORTS
#define CROSSCOVARIANCEMH_API __declspec(dllexport)
#else
#define CROSSCOVARIANCEMH_API __declspec(dllimport)
#endif

/*
 * Computes the cross-covariance matrix between two data matrices.
 *
 * @param size_a   Number of rows (variables) in matrix A
 * @param size_b   Number of rows (variables) in matrix B
 * @param nsamples Number of samples (columns) in each matrix
 * @param matrix_a matrix A, size_a x nsamples
 * @param matrix_b matrix B, size_b x nsamples
 * @return         result matrix (size_b x size_a), caller must free
 */

extern "C" CROSSCOVARIANCEMH_API void cross_cov(int size_a, int size_b, int nsamples, double matrix_a[1000000], double matrix_b[1000000], double matrix_c[100000]);
