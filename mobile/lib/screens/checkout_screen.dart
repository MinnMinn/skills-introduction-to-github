/// Checkout screen — card entry with biometric confirmation.
///
/// PCI compliance:
///   - Card entry uses flutter_stripe's CardField widget.
///   - Raw PAN never touches our code; Stripe SDK tokenises it to a
///     payment_method_id which is the only value we pass to the backend.
///
/// Flow:
///   1. User fills in amount (pre-filled or from navigation args).
///   2. User enters card via Stripe CardField (SDK-managed).
///   3. Biometric authentication is requested before submission.
///   4. On biometric success → createPaymentMethod → createIntent API call
///      → Stripe confirmPayment → polling / webhook updates status.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_stripe/flutter_stripe.dart';
import 'package:local_auth/local_auth.dart';
import 'package:uuid/uuid.dart';

import '../services/payment_service.dart';
import '../widgets/payment_status_widget.dart';

// ── Providers ─────────────────────────────────────────────────────────────────

/// Idempotency key provider — regenerated on each checkout session.
final _idempotencyKeyProvider = Provider<String>((_) => const Uuid().v4());

// ── Screen ────────────────────────────────────────────────────────────────────

class CheckoutScreen extends ConsumerStatefulWidget {
  const CheckoutScreen({
    super.key,
    required this.amountCents,
    required this.currency,
    required this.customerId,
    required this.paymentService,
    this.localAuth,
  });

  final int amountCents;
  final String currency;
  final String customerId;
  final PaymentService paymentService;
  final LocalAuthentication? localAuth;

  @override
  ConsumerState<CheckoutScreen> createState() => _CheckoutScreenState();
}

class _CheckoutScreenState extends ConsumerState<CheckoutScreen> {
  final _formKey = GlobalKey<FormState>();
  PaymentUiState _uiState = PaymentUiState.idle;
  String? _errorMessage;
  String? _paymentId;
  bool _cardComplete = false;
  int _retryCount = 0;
  static const int _maxRetries = 3;

  late final LocalAuthentication _localAuth;
  late final String _idempotencyKey;

  @override
  void initState() {
    super.initState();
    _localAuth = widget.localAuth ?? LocalAuthentication();
    _idempotencyKey = const Uuid().v4();
  }

  // ── Biometric authentication ───────────────────────────────────────────────

  Future<bool> _requestBiometricAuth() async {
    try {
      final canCheck = await _localAuth.canCheckBiometrics;
      if (!canCheck) {
        // Device doesn't support biometrics — fall through to PIN fallback
        return await _localAuth.authenticate(
          localizedReason: 'Confirm payment of '
              '${(widget.amountCents / 100).toStringAsFixed(2)} '
              '${widget.currency.toUpperCase()}',
          options: const AuthenticationOptions(
            biometricOnly: false,
            stickyAuth: true,
          ),
        );
      }
      return await _localAuth.authenticate(
        localizedReason: 'Use biometrics to confirm your payment of '
            '${(widget.amountCents / 100).toStringAsFixed(2)} '
            '${widget.currency.toUpperCase()}',
        options: const AuthenticationOptions(
          biometricOnly: true,
          stickyAuth: true,
        ),
      );
    } catch (e) {
      debugPrint('Biometric auth error: $e');
      return false;
    }
  }

  // ── Payment submission ─────────────────────────────────────────────────────

  Future<void> _submitPayment() async {
    if (!_formKey.currentState!.validate()) return;
    if (!_cardComplete) {
      _showError('Please complete your card details.');
      return;
    }

    // 1. Biometric confirmation
    setState(() => _uiState = PaymentUiState.loading);
    final authenticated = await _requestBiometricAuth();
    if (!authenticated) {
      setState(() {
        _uiState = PaymentUiState.failure;
        _errorMessage = 'Biometric authentication failed. Please try again.';
      });
      return;
    }

    await _performPayment();
  }

  Future<void> _performPayment() async {
    setState(() {
      _uiState = _retryCount > 0 ? PaymentUiState.retrying : PaymentUiState.loading;
      _errorMessage = null;
    });

    try {
      // 2. Tokenise card via Stripe SDK (PCI: raw PAN never leaves the SDK)
      final paymentMethod = await Stripe.instance.createPaymentMethod(
        params: const PaymentMethodParams.card(
          paymentMethodData: PaymentMethodData(),
        ),
      );

      // 3. Create intent on backend (receives only token, not card number)
      final result = await widget.paymentService.createIntent(
        amountCents: widget.amountCents,
        currency: widget.currency,
        customerId: widget.customerId,
        paymentMethodId: paymentMethod.id,
        idempotencyKey: _idempotencyKey,
      );

      // 4. Confirm payment with Stripe SDK
      await Stripe.instance.confirmPayment(
        paymentIntentClientSecret: result.clientSecret,
        data: const PaymentMethodParams.card(
          paymentMethodData: PaymentMethodData(),
        ),
      );

      // 5. Poll for final status
      final status = await widget.paymentService.getPaymentStatus(result.paymentId);

      if (status.status == 'succeeded') {
        setState(() {
          _uiState = PaymentUiState.success;
          _paymentId = result.paymentId;
          _retryCount = 0;
        });
      } else if (status.status == 'failed') {
        setState(() {
          _uiState = PaymentUiState.failure;
          _errorMessage = 'Payment was declined. Please try a different card.';
        });
      } else {
        // Still processing — treat as success with note
        setState(() {
          _uiState = PaymentUiState.success;
          _paymentId = result.paymentId;
        });
      }
    } on StripeException catch (e) {
      setState(() {
        _uiState = PaymentUiState.failure;
        _errorMessage = e.error.localizedMessage ?? 'Card payment failed.';
      });
    } on PaymentApiException catch (e) {
      if (e.statusCode == 429) {
        setState(() {
          _uiState = PaymentUiState.failure;
          _errorMessage = 'Too many payment attempts. Please wait a moment.';
        });
      } else {
        setState(() {
          _uiState = PaymentUiState.failure;
          _errorMessage = 'Payment service unavailable. Please try again.';
        });
      }
    } catch (e) {
      setState(() {
        _uiState = PaymentUiState.failure;
        _errorMessage = 'An unexpected error occurred. Please try again.';
      });
    }
  }

  void _retry() {
    if (_retryCount >= _maxRetries) {
      _showError('Maximum retry attempts reached. Please contact support.');
      return;
    }
    _retryCount++;
    _performPayment();
  }

  void _showError(String message) {
    setState(() {
      _uiState = PaymentUiState.failure;
      _errorMessage = message;
    });
  }

  // ── Build ──────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final amountFormatted =
        '${(widget.amountCents / 100).toStringAsFixed(2)} ${widget.currency.toUpperCase()}';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Checkout'),
        centerTitle: true,
      ),
      body: SafeArea(
        child: _uiState == PaymentUiState.idle
            ? _buildForm(context, amountFormatted)
            : Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: PaymentStatusWidget(
                    state: _uiState,
                    errorMessage: _errorMessage,
                    paymentId: _paymentId,
                    onRetry: _retry,
                    onDone: () => Navigator.of(context).pop(),
                  ),
                ),
              ),
      ),
    );
  }

  Widget _buildForm(BuildContext context, String amountFormatted) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // ── Amount display ────────────────────────────────────────────
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Amount',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    Text(
                      amountFormatted,
                      key: const Key('amount_display'),
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // ── Stripe card field (SDK-managed, PCI-compliant) ────────────
            Text(
              'Card details',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            CardField(
              key: const Key('stripe_card_field'),
              onCardChanged: (card) {
                setState(() => _cardComplete = card?.complete ?? false);
              },
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: 'Card number',
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              '🔒 Card data is tokenised by Stripe — we never see your card number.',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
            const SizedBox(height: 32),

            // ── Biometric notice ─────────────────────────────────────────
            Row(
              children: const [
                Icon(Icons.fingerprint, color: Colors.blueGrey),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Biometric confirmation required before payment.',
                    style: TextStyle(fontSize: 13),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // ── Submit button ─────────────────────────────────────────────
            ElevatedButton.icon(
              key: const Key('pay_button'),
              onPressed: _cardComplete ? _submitPayment : null,
              icon: const Icon(Icons.lock),
              label: Text('Pay $amountFormatted'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
