/// Payment API service — communicates with the FastAPI backend.
///
/// PCI note: raw card data NEVER passes through this service.
/// The Stripe SDK tokenises the card client-side and returns a [paymentMethodId].
/// Only that token is sent to the backend.
library;

import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:uuid/uuid.dart';

/// Result of a create-intent call.
class CreateIntentResult {
  const CreateIntentResult({
    required this.paymentId,
    required this.clientSecret,
    required this.status,
    required this.idempotent,
  });

  final String paymentId;
  final String clientSecret;
  final String status;
  final bool idempotent;

  factory CreateIntentResult.fromJson(Map<String, dynamic> json) {
    return CreateIntentResult(
      paymentId: json['payment_id'] as String,
      clientSecret: json['client_secret'] as String,
      status: json['status'] as String,
      idempotent: json['idempotent'] as bool? ?? false,
    );
  }
}

/// Current status of a payment.
class PaymentStatus {
  const PaymentStatus({
    required this.paymentId,
    required this.status,
    required this.amount,
    required this.currency,
    required this.customerIdMasked,
  });

  final String paymentId;
  final String status;
  final int amount;
  final String currency;
  final String customerIdMasked;

  factory PaymentStatus.fromJson(Map<String, dynamic> json) {
    return PaymentStatus(
      paymentId: json['payment_id'] as String,
      status: json['status'] as String,
      amount: json['amount'] as int,
      currency: json['currency'] as String,
      customerIdMasked: json['customer_id_masked'] as String,
    );
  }
}

/// Thrown when the API returns an error response.
class PaymentApiException implements Exception {
  const PaymentApiException({required this.statusCode, required this.message});

  final int statusCode;
  final String message;

  @override
  String toString() => 'PaymentApiException($statusCode): $message';
}

class PaymentService {
  PaymentService({
    required String baseUrl,
    required String userId,
    Dio? dio,
  })  : _userId = userId,
        _dio = dio ??
            Dio(BaseOptions(
              baseUrl: baseUrl,
              connectTimeout: const Duration(seconds: 15),
              receiveTimeout: const Duration(seconds: 30),
              headers: {'Content-Type': 'application/json'},
            ));

  final Dio _dio;
  final String _userId;
  final _uuid = const Uuid();

  /// Create a Stripe PaymentIntent on the backend.
  ///
  /// [paymentMethodId] is the token produced by the Stripe SDK — no raw PAN.
  /// [idempotencyKey] is generated if not supplied (UUID v4).
  Future<CreateIntentResult> createIntent({
    required int amountCents,
    required String currency,
    required String customerId,
    String? paymentMethodId,
    String? idempotencyKey,
    Map<String, dynamic> metadata = const {},
  }) async {
    final key = idempotencyKey ?? _uuid.v4();
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/payments/create-intent',
        data: {
          'amount': amountCents,
          'currency': currency,
          'customer_id': customerId,
          'idempotency_key': key,
          if (paymentMethodId != null) 'payment_method_id': paymentMethodId,
          'metadata': metadata,
        },
        options: Options(headers: {'X-User-ID': _userId}),
      );
      return CreateIntentResult.fromJson(response.data!);
    } on DioException catch (e) {
      throw _wrapDioError(e);
    }
  }

  /// Fetch the current status of a payment.
  Future<PaymentStatus> getPaymentStatus(String paymentId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/payments/$paymentId',
        options: Options(headers: {'X-User-ID': _userId}),
      );
      return PaymentStatus.fromJson(response.data!);
    } on DioException catch (e) {
      throw _wrapDioError(e);
    }
  }

  PaymentApiException _wrapDioError(DioException e) {
    final status = e.response?.statusCode ?? 0;
    final detail =
        (e.response?.data as Map<String, dynamic>?)?['detail'] as String? ??
            e.message ??
            'Unknown error';
    return PaymentApiException(statusCode: status, message: detail);
  }
}
