/// App entry point.
library;

import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_stripe/flutter_stripe.dart';

import 'screens/checkout_screen.dart';
import 'services/payment_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await dotenv.load(fileName: '.env');

  // Initialise the Stripe SDK with the publishable key.
  // Note: the publishable key is NOT a secret — it is safe to embed in the app.
  Stripe.publishableKey = dotenv.env['STRIPE_PUBLISHABLE_KEY'] ?? '';
  await Stripe.instance.applySettings();

  runApp(const ProviderScope(child: PaymentsApp()));
}

class PaymentsApp extends StatelessWidget {
  const PaymentsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Payments',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
        useMaterial3: true,
      ),
      home: CheckoutScreen(
        amountCents: 1000, // $10.00
        currency: 'USD',
        customerId: 'cust_demo',
        paymentService: PaymentService(
          baseUrl: dotenv.env['API_BASE_URL'] ?? 'https://api.example.com',
          userId: dotenv.env['USER_ID'] ?? 'user_demo',
        ),
      ),
    );
  }
}
