/// Widget tests for the CheckoutScreen.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:payments_app/screens/checkout_screen.dart';
import 'package:payments_app/services/payment_service.dart';
import 'package:payments_app/widgets/payment_status_widget.dart';
import 'package:local_auth/local_auth.dart';

// ── Mocks ─────────────────────────────────────────────────────────────────────

class MockPaymentService extends Mock implements PaymentService {}
class MockLocalAuthentication extends Mock implements LocalAuthentication {}

// ── Helpers ───────────────────────────────────────────────────────────────────

Widget _buildTestApp({
  required PaymentService paymentService,
  LocalAuthentication? localAuth,
  int amountCents = 1000,
  String currency = 'USD',
  String customerId = 'cust_test',
}) {
  return ProviderScope(
    child: MaterialApp(
      home: CheckoutScreen(
        amountCents: amountCents,
        currency: currency,
        customerId: customerId,
        paymentService: paymentService,
        localAuth: localAuth,
      ),
    ),
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

void main() {
  late MockPaymentService mockPaymentService;
  late MockLocalAuthentication mockLocalAuth;

  setUp(() {
    mockPaymentService = MockPaymentService();
    mockLocalAuth = MockLocalAuthentication();
  });

  group('CheckoutScreen — initial state', () {
    testWidgets('shows amount in header', (tester) async {
      await tester.pumpWidget(_buildTestApp(
        paymentService: mockPaymentService,
        amountCents: 1000,
        currency: 'USD',
      ));
      await tester.pumpAndSettle();

      // Amount display shows formatted value
      expect(find.byKey(const Key('amount_display')), findsOneWidget);
      expect(find.text('10.00 USD'), findsOneWidget);
    });

    testWidgets('pay button is disabled when card not complete', (tester) async {
      await tester.pumpWidget(_buildTestApp(paymentService: mockPaymentService));
      await tester.pumpAndSettle();

      final payButton = tester.widget<ElevatedButton>(
        find.byKey(const Key('pay_button')),
      );
      expect(payButton.onPressed, isNull);
    });

    testWidgets('shows biometric notice', (tester) async {
      await tester.pumpWidget(_buildTestApp(paymentService: mockPaymentService));
      await tester.pumpAndSettle();

      expect(find.text('Biometric confirmation required before payment.'),
          findsOneWidget);
    });

    testWidgets('shows Stripe card field', (tester) async {
      await tester.pumpWidget(_buildTestApp(paymentService: mockPaymentService));
      await tester.pumpAndSettle();

      // CardField widget should be present
      expect(find.byKey(const Key('stripe_card_field')), findsOneWidget);
    });
  });

  group('PaymentStatusWidget', () {
    testWidgets('success state shows title and done button', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: PaymentStatusWidget(
              state: PaymentUiState.success,
              paymentId: 'pay_test_123',
            ),
          ),
        ),
      );

      expect(find.byKey(const Key('success_title')), findsOneWidget);
      expect(find.byKey(const Key('done_button')), findsOneWidget);
      expect(find.text('pay_test_123'), findsOneWidget);
    });

    testWidgets('failure state shows error message and retry button', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: PaymentStatusWidget(
              state: PaymentUiState.failure,
              errorMessage: 'Card was declined.',
            ),
          ),
        ),
      );

      expect(find.byKey(const Key('failure_title')), findsOneWidget);
      expect(find.byKey(const Key('retry_button')), findsOneWidget);
      expect(find.byKey(const Key('cancel_button')), findsOneWidget);
      expect(find.byKey(const Key('error_message')), findsOneWidget);
      expect(find.text('Card was declined.'), findsOneWidget);
    });

    testWidgets('loading state shows progress indicator', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: PaymentStatusWidget(state: PaymentUiState.loading),
          ),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('Processing payment…'), findsOneWidget);
    });

    testWidgets('retrying state shows retrying message', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: PaymentStatusWidget(state: PaymentUiState.retrying),
          ),
        ),
      );

      expect(find.text('Retrying payment…'), findsOneWidget);
    });

    testWidgets('idle state renders nothing', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: PaymentStatusWidget(state: PaymentUiState.idle),
          ),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(find.byKey(const Key('success_title')), findsNothing);
    });

    testWidgets('retry callback fires on retry button tap', (tester) async {
      var retryTapped = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PaymentStatusWidget(
              state: PaymentUiState.failure,
              errorMessage: 'Failed',
              onRetry: () => retryTapped = true,
            ),
          ),
        ),
      );

      await tester.tap(find.byKey(const Key('retry_button')));
      await tester.pump();
      expect(retryTapped, isTrue);
    });
  });

  group('PaymentService — unit tests', () {
    test('CreateIntentResult.fromJson parses correctly', () {
      final result = CreateIntentResult.fromJson({
        'payment_id': 'pay_abc',
        'client_secret': 'pi_abc_secret',
        'status': 'pending',
        'idempotent': false,
      });
      expect(result.paymentId, 'pay_abc');
      expect(result.clientSecret, 'pi_abc_secret');
      expect(result.status, 'pending');
      expect(result.idempotent, isFalse);
    });

    test('CreateIntentResult.fromJson defaults idempotent to false', () {
      final result = CreateIntentResult.fromJson({
        'payment_id': 'pay_xyz',
        'client_secret': 'secret',
        'status': 'pending',
      });
      expect(result.idempotent, isFalse);
    });

    test('PaymentStatus.fromJson parses correctly', () {
      final status = PaymentStatus.fromJson({
        'payment_id': 'pay_123',
        'status': 'succeeded',
        'amount': 1000,
        'currency': 'USD',
        'customer_id_masked': 'cust****',
      });
      expect(status.status, 'succeeded');
      expect(status.customerIdMasked, 'cust****');
    });
  });
}
