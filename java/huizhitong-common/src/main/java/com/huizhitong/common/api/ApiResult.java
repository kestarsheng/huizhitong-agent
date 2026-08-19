package com.huizhitong.common.api;

public record ApiResult<T>(int code, String message, T data, String traceId) {
    public static <T> ApiResult<T> success(T data, String traceId) {
        return new ApiResult<>(ResultCode.SUCCESS.getCode(), ResultCode.SUCCESS.getMessage(), data, traceId);
    }

    public static <T> ApiResult<T> failure(ResultCode resultCode, String traceId) {
        return new ApiResult<>(resultCode.getCode(), resultCode.getMessage(), null, traceId);
    }

    public static <T> ApiResult<T> failure(int code, String message, String traceId) {
        return new ApiResult<>(code, message, null, traceId);
    }
}
