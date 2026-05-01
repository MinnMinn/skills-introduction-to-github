/// Payment status display widget — shows success, failure, or retry state.
library;

import 'package:flutter/material.dart';

enum PaymentUiState { idle, loading, success, failure, retrying }

class PaymentStatusWidget extends StatelessWidget {
  const PaymentStatusWidget({
    super.key,
    required this.state,
    this.errorMessage,
    this.paymentId,
    this.onRetry,
    this.onDone,
  });

  final PaymentUiState state;
  final String? errorMessage;
  final String? paymentId;
  final VoidCallback? onRetry;
  final VoidCallback? onDone;

  @override
  Widget build(BuildContext context) {
    return switch (state) {
      PaymentUiState.loading || PaymentUiState.retrying => _buildLoading(context),
      PaymentUiState.success => _buildSuccess(context),
      PaymentUiState.failure => _buildFailure(context),
      PaymentUiState.idle => const SizedBox.shrink(),
    };
  }

  Widget _buildLoading(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const CircularProgressIndicator(),
        const SizedBox(height: 16),
        Text(
          state == PaymentUiState.retrying ? 'Retrying payment…' : 'Processing payment…',
          style: Theme.of(context).textTheme.bodyLarge,
        ),
      ],
    );
  }

  Widget _buildSuccess(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(Icons.check_circle_outline, color: Colors.green, size: 72),
        const SizedBox(height: 16),
        Text(
          'Payment successful!',
          key: const Key('success_title'),
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: Colors.green,
              ),
        ),
        if (paymentId != null) ...[
          const SizedBox(height: 8),
          Text(
            'Reference: $paymentId',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
        const SizedBox(height: 24),
        ElevatedButton(
          key: const Key('done_button'),
          onPressed: onDone,
          child: const Text('Done'),
        ),
      ],
    );
  }

  Widget _buildFailure(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(Icons.error_outline, color: Colors.red, size: 72),
        const SizedBox(height: 16),
        Text(
          'Payment failed',
          key: const Key('failure_title'),
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: Colors.red,
              ),
        ),
        if (errorMessage != null) ...[
          const SizedBox(height: 8),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Text(
              errorMessage!,
              key: const Key('error_message'),
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
        const SizedBox(height: 24),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            OutlinedButton(
              key: const Key('cancel_button'),
              onPressed: onDone,
              child: const Text('Cancel'),
            ),
            const SizedBox(width: 16),
            ElevatedButton(
              key: const Key('retry_button'),
              onPressed: onRetry,
              child: const Text('Retry'),
            ),
          ],
        ),
      ],
    );
  }
}
