import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import useAuthStore from '../stores/authStore';
import useServiceStore from '../stores/serviceStore';
import { getErrorMessage } from '../api/client';
import { useTheme, SIZES, SHADOW } from '../theme';
import { useNotificationStore } from '../stores/notificationStore';

export default function RegisterScreen({ navigation }) {
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();
  const styles = getStyles(colors);
  const register = useAuthStore((s) => s.register);
  const signIn = useAuthStore((s) => s.signIn);
  const isLoading = useAuthStore((s) => s.isLoading);

  const services = useServiceStore((s) => s.services);
  const fetchServices = useServiceStore((s) => s.fetchServices);
  const servicesLoading = useServiceStore((s) => s.isLoading);
  const showToast = useNotificationStore((s) => s.showToast);

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [role, setRole] = useState('customer');
  const [serviceCategory, setServiceCategory] = useState('');
  const [hourlyRate, setHourlyRate] = useState('');
  const [aadhar, setAadhar] = useState('');
  const [pan, setPan] = useState('');

  useEffect(() => {
    fetchServices();
  }, [fetchServices]);

  useEffect(() => {
    if (services.length > 0 && !serviceCategory) {
      setServiceCategory(services[0].name);
    }
  }, [services, serviceCategory]);

  const handleRegister = async () => {
    if (!name || !email || !password || !phone || !address) {
      showToast('warning', 'Missing Details', 'Please fill in all required fields.');
      return;
    }

    const payload = { name, email, password, phone, address, role };

    if (role === 'partner') {
      if (!serviceCategory || !hourlyRate || !aadhar || !pan) {
        showToast('warning', 'Missing Info', 'Please complete all partner fields.');
        return;
      }
      payload.service_category = serviceCategory;
      payload.hourly_rate = parseFloat(hourlyRate);
      payload.aadhar_card = aadhar;
      payload.pan_card = pan.toUpperCase();
    }

    try {
      const data = await register(payload);
      await signIn(data);
      showToast('success', 'Account Created', 'Welcome to Purakam!');
    } catch (error) {


      showToast('error', 'Registration Error', getErrorMessage(error, 'Registration failed'));
    }
  };

  return (
    <SafeAreaView
      style={[styles.container, { paddingTop: insets.top, paddingLeft: insets.left, paddingRight: insets.right }]}
    >
      <ScrollView
        contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + 24 }]}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.title}>Create your Purakam account</Text>
        <Text style={styles.subtitle}>Sign up to book trusted local home services.</Text>

        <View style={styles.formGroup}>
          <Text style={styles.label}>Full Name</Text>
          <TextInput style={styles.input} value={name} onChangeText={setName} placeholder="Name" placeholderTextColor={colors.textMuted} />
        </View>
        <View style={styles.formGroup}>
          <Text style={styles.label}>Email</Text>
          <TextInput style={styles.input} value={email} onChangeText={setEmail} placeholder="hello@purakam.in" keyboardType="email-address" autoCapitalize="none" placeholderTextColor={colors.textMuted} />
        </View>
        <View style={styles.formGroup}>
          <Text style={styles.label}>Password</Text>
          <View style={styles.passwordContainer}>
            <TextInput
              style={[styles.input, styles.passwordInput]}
              value={password}
              onChangeText={setPassword}
              placeholder="Password"
              secureTextEntry={!showPassword}
              placeholderTextColor={colors.textMuted}
            />
            <TouchableOpacity onPress={() => setShowPassword(!showPassword)} style={styles.eyeButton}>
              <MaterialCommunityIcons name={showPassword ? 'eye-off-outline' : 'eye-outline'} size={22} color={colors.textSecondary} />
            </TouchableOpacity>
          </View>
        </View>
        <View style={styles.formGroup}>
          <Text style={styles.label}>Phone</Text>
          <TextInput style={styles.input} value={phone} onChangeText={setPhone} placeholder="+91 9999 0000 99" keyboardType="phone-pad" placeholderTextColor={colors.textMuted} />
        </View>
        <View style={styles.formGroup}>
          <Text style={styles.label}>Address (Mumbai / Thane / Navi Mumbai)</Text>
          <TextInput style={[styles.input, { height: 100 }]} value={address} onChangeText={setAddress} placeholder="Full doorstep address" multiline placeholderTextColor={colors.textMuted} />
        </View>

        <View style={styles.switchRow}>
          <TouchableOpacity style={[styles.switchButton, role === 'customer' && styles.switchButtonActive]} onPress={() => setRole('customer')}>
            <Text style={[styles.switchText, role === 'customer' && styles.switchTextActive]}>Customer</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.switchButton, role === 'partner' && styles.switchButtonActive]} onPress={() => setRole('partner')}>
            <Text style={[styles.switchText, role === 'partner' && styles.switchTextActive]}>Partner</Text>
          </TouchableOpacity>
        </View>

        {role === 'partner' && (
          <View style={styles.partnerSection}>
            <View style={styles.formGroup}>
              <Text style={styles.label}>Service Category</Text>
              {servicesLoading ? (
                <ActivityIndicator color={colors.accent} />
              ) : services.length === 0 ? (
                <Text style={styles.hintText}>No categories available. Check your connection.</Text>
              ) : (
                <View style={styles.categoryGrid}>
                  {services.map((cat) => (
                    <TouchableOpacity
                      key={cat.id}
                      style={[styles.categoryChip, serviceCategory === cat.name && styles.categoryChipActive]}
                      onPress={() => setServiceCategory(cat.name)}
                    >
                      <Text style={[styles.categoryChipText, serviceCategory === cat.name && styles.categoryChipTextActive]}>
                        {cat.name}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}
            </View>
            <View style={styles.formGroup}>
              <Text style={styles.label}>Hourly Rate (INR)</Text>
              <TextInput style={styles.input} value={hourlyRate} onChangeText={setHourlyRate} keyboardType="numeric" placeholder="499" placeholderTextColor={colors.textMuted} />
            </View>
            <View style={styles.formGroup}>
              <Text style={styles.label}>Aadhar Card (12 digits)</Text>
              <TextInput style={styles.input} value={aadhar} onChangeText={setAadhar} placeholder="123456789012" keyboardType="numeric" maxLength={12} placeholderTextColor={colors.textMuted} />
            </View>
            <View style={styles.formGroup}>
              <Text style={styles.label}>PAN Card</Text>
              <TextInput style={styles.input} value={pan} onChangeText={setPan} placeholder="ABCDE1234F" autoCapitalize="characters" maxLength={10} placeholderTextColor={colors.textMuted} />
            </View>
          </View>
        )}

        <TouchableOpacity style={styles.button} onPress={handleRegister} disabled={isLoading}>
          <Text style={styles.buttonText}>{isLoading ? 'Creating account...' : 'Create Account'}</Text>
        </TouchableOpacity>

        <View style={styles.footerTextRow}>
          <Text style={styles.footerText}>Already have an account?</Text>
          <TouchableOpacity onPress={() => navigation.navigate('Login')}>
            <Text style={styles.footerLink}> Sign in</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const getStyles = (colors) =>
  StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.background },
    content: { paddingHorizontal: SIZES.padding + 10, paddingTop: 24 },
    title: { fontSize: 30, fontWeight: '700', color: colors.textPrimary, marginBottom: 8 },
    subtitle: { fontSize: 16, color: colors.textSecondary, marginBottom: 24 },
    formGroup: { marginBottom: 16 },
    label: { fontSize: 14, color: colors.textSecondary, marginBottom: 8, fontWeight: '600' },
    input: {
      backgroundColor: colors.surface,
      borderRadius: SIZES.radius,
      padding: 14,
      color: colors.textPrimary,
    },
    passwordContainer: {
      flexDirection: 'row',
      alignItems: 'center',
      borderRadius: SIZES.radius,
      backgroundColor: colors.surface,
    },
    passwordInput: { flex: 1, borderWidth: 0, marginBottom: 0, padding: 14, color: colors.textPrimary, backgroundColor: 'transparent' },
    eyeButton: { paddingHorizontal: 12, justifyContent: 'center', alignItems: 'center'},
    switchRow: {
      flexDirection: 'row',
      marginBottom: 24,
      borderRadius: SIZES.radius,
      overflow: 'hidden',
      backgroundColor: colors.surface,
    },
    switchButton: { flex: 1, padding: 14, alignItems: 'center' },
    switchButtonActive: { backgroundColor: colors.primary },
    switchText: { fontWeight: '600', color: colors.textSecondary },
    switchTextActive: { color: colors.accentDark },
    button: {
      marginTop: 8,
      backgroundColor: colors.primary,
      padding: 16,
      borderRadius: SIZES.radius,
      alignItems: 'center',
      ...SHADOW,
    },
    buttonText: { color: colors.accentDark, fontWeight: '700', fontSize: 16 },
    footerTextRow: { marginTop: 22, flexDirection: 'row', justifyContent: 'center' },
    footerText: { color: colors.textSecondary },
    footerLink: { color: colors.primary, fontWeight: '700' },
    partnerSection: {
      marginBottom: 16,
      padding: 16,
      backgroundColor: colors.surface,
      borderRadius: SIZES.radius,
    },
    categoryGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
    categoryChip: {
      paddingHorizontal: 12,
      paddingVertical: 8,
      borderRadius: 8,
      backgroundColor: colors.card,
    },
    categoryChipActive: { backgroundColor: colors.primary },
    categoryChipText: { color: colors.textSecondary, fontSize: 12, fontWeight: '600' },
    categoryChipTextActive: { color: colors.accentDark },
    hintText: { color: colors.textMuted, fontStyle: 'italic' },
  });
