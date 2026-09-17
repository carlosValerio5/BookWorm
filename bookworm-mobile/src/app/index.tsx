import { useState, useRef } from 'react';
import { StyleSheet, Pressable, View, Text, ActivityIndicator, Modal, type LayoutChangeEvent } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { realBookScan, type ScanResult } from '../services/api';
import { useBooks } from '../context/BookContext';
import { useLiveDetection } from '../hooks/use-live-detection';
import { scaleBoxToPreview, type Size } from '../hooks/live-detection-geometry';
import { StarAccent } from '@/components/star-accent';
import { BookWormPalette, Colors, Radius, Spacing } from '@/constants/theme';

const c = Colors.dark;

export default function HomeScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [loading, setLoading] = useState(false);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const cameraRef = useRef<any>(null);
  const [previewSize, setPreviewSize] = useState<Size | null>(null);
  const [isCameraReady, setIsCameraReady] = useState(false);
  const { box: liveBox, frameSize: liveFrameSize } = useLiveDetection(cameraRef, isCameraActive && isCameraReady);
  const [foundBook, setFoundBook] = useState<ScanResult | null>(null);
  const { addBook } = useBooks();

  const handleCameraLayout = (event: LayoutChangeEvent) => {
    const { width, height } = event.nativeEvent.layout;
    setPreviewSize({ width, height });
  };

  const encenderCamara = async () => {
    setErrorMessage(null);
    if (!permission?.granted) await requestPermission();
    setIsCameraReady(false);
    setIsCameraActive(true);
  };

  const escanearLibroReal = async () => {
    if (loading || !isCameraReady) return;
    setLoading(true);
    setErrorMessage(null);

    try {
      if (cameraRef.current) {
        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.8,
          skipProcessing: true,
        });

        const resultado = await realBookScan(photo.uri);

        if (resultado.success && resultado.data) {
          setFoundBook(resultado.data);
          setIsCameraActive(false);
        } else {
          setErrorMessage(resultado.message || 'No se pudo reconocer el libro. Intenta enfocar mejor la portada.');
          setIsCameraActive(false);
        }
      }
    } catch (error) {
      console.error('Error al capturar:', error);
      setErrorMessage('Error al procesar la foto. Intenta de nuevo.');
      setIsCameraActive(false);
    } finally {
      setLoading(false);
    }
  };

  const guardarLibro = () => {
    if (foundBook) {
      addBook({ isbn: foundBook.isbn });
      setFoundBook(null);
      alert('¡Libro guardado en tu biblioteca!');
    }
  };

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <View style={styles.titleRow}>
            <StarAccent size={12} dim />
            <Text style={styles.title}>BookWorm</Text>
            <StarAccent size={12} dim />
          </View>
          <View style={styles.versionBadge}>
            <Text style={styles.version}>v0.1.0</Text>
          </View>
        </View>

        {errorMessage && (
          <View style={styles.errorBanner}>
            <Text style={styles.errorBannerText}>{errorMessage}</Text>
          </View>
        )}

        {!isCameraActive ? (
          <Pressable style={styles.cameraBoxPlaceholder} onPress={encenderCamara}>
            <StarAccent size={22} />
            <View style={styles.liveDot} />
            <Text style={styles.cameraTitle}>Escanear portada o contraportada</Text>
            <Text style={styles.cameraSubtitle}>Toca aquí para abrir la cámara</Text>
          </Pressable>
        ) : (
          <View style={styles.cameraBoxActive} onLayout={handleCameraLayout}>
            {permission?.granted ? (
              <>
                <CameraView
                  style={styles.camera}
                  facing="back"
                  ref={cameraRef}
                  onCameraReady={() => setIsCameraReady(true)}
                />
                {liveBox && liveFrameSize && previewSize && (
                  <View
                    pointerEvents="none"
                    style={[styles.liveDetectionBox, scaleBoxToPreview(liveBox, liveFrameSize, previewSize)]}
                  />
                )}
                <View style={styles.cameraGoldFrame} pointerEvents="none" />
                <Pressable style={styles.cameraOverlayAbsolute} onPress={escanearLibroReal}>
                  {loading ? (
                    <ActivityIndicator size="large" color={BookWormPalette.gold} />
                  ) : (
                    <View style={styles.scanHintPill}>
                      <StarAccent size={11} />
                      <Text style={styles.scanHintText}>Enfoca el libro y toca para identificar</Text>
                    </View>
                  )}
                </Pressable>
              </>
            ) : (
              <View style={styles.cameraBoxPlaceholder}>
                <Text style={styles.infoText}>Falta permiso de cámara</Text>
              </View>
            )}
          </View>
        )}

        <Modal visible={!!foundBook} transparent animationType="fade">
          <View style={styles.modalOverlay}>
            <View style={styles.modalCard}>
              <View style={styles.modalPreRow}>
                <StarAccent size={13} />
                <Text style={styles.modalPre}>
                  {foundBook?.kind === 'isbn' ? 'ISBN encontrado' : 'Portada detectada'}
                </Text>
                <StarAccent size={13} />
              </View>
              <Text style={styles.modalTitle}>
                {foundBook?.isbn ? `ISBN ${foundBook.isbn}` : 'Sin ISBN leído'}
              </Text>
              <Text style={styles.modalAuthor}>
                {foundBook?.texts && foundBook.texts.length > 0
                  ? foundBook.texts.map((text) => text.text).join(' · ')
                  : 'Sin texto legible en la portada'}
              </Text>

              <Pressable style={styles.saveButton} onPress={guardarLibro}>
                <Text style={styles.saveButtonText}>Guardar en mi biblioteca</Text>
              </Pressable>

              <Pressable onPress={() => setFoundBook(null)} style={styles.cancelPress}>
                <Text style={styles.cancelText}>Cancelar</Text>
              </Pressable>
            </View>
          </View>
        </Modal>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: c.background },
  safeArea: {
    flex: 1,
    paddingHorizontal: Spacing.screen,
    justifyContent: 'space-between',
    paddingVertical: Spacing.pane,
  },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  title: { fontSize: 22, fontWeight: '500', color: c.text },
  versionBadge: {
    borderWidth: 1,
    borderColor: c.goldLine,
    paddingVertical: Spacing.xs,
    paddingHorizontal: Spacing.md,
    borderRadius: Radius.pill,
  },
  version: { color: c.gold, fontSize: 12, fontVariant: ['tabular-nums'] },

  errorBanner: {
    backgroundColor: 'rgba(207, 45, 86, 0.14)',
    borderWidth: 1,
    borderColor: 'rgba(207, 45, 86, 0.35)',
    padding: Spacing.md,
    borderRadius: Radius.row,
    marginTop: Spacing.md,
  },
  errorBannerText: {
    color: 'rgba(237, 236, 236, 0.92)',
    fontSize: 13,
    fontWeight: '500',
    textAlign: 'center',
  },
  cameraBoxPlaceholder: {
    backgroundColor: c.backgroundElement,
    borderWidth: 1,
    borderColor: c.goldLine,
    borderStyle: 'dashed',
    borderRadius: Radius.frame,
    width: '100%',
    height: '90%',
    alignSelf: 'center',
    justifyContent: 'center',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  liveDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: BookWormPalette.gold,
    marginBottom: Spacing.xs,
  },
  cameraTitle: {
    fontSize: 17,
    fontWeight: '500',
    color: c.text,
    marginTop: Spacing.xs,
    marginBottom: Spacing.xs,
    textAlign: 'center',
    paddingHorizontal: Spacing.group,
  },
  cameraSubtitle: { color: c.textSecondary, fontSize: 13, textAlign: 'center' },

  cameraBoxActive: {
    width: '100%',
    height: '90%',
    borderRadius: Radius.frame,
    overflow: 'hidden',
    alignSelf: 'center',
    borderWidth: 1,
    borderColor: c.border,
    position: 'relative',
  },
  camera: { flex: 1 },
  cameraGoldFrame: {
    ...StyleSheet.absoluteFillObject,
    borderWidth: 1,
    borderColor: BookWormPalette.goldLine,
    borderRadius: Radius.frame,
    margin: Spacing.md,
  },
  liveDetectionBox: {
    position: 'absolute',
    borderWidth: 2,
    borderColor: BookWormPalette.gold,
    borderRadius: Radius.row,
  },
  cameraOverlayAbsolute: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(20, 18, 11, 0.2)',
    justifyContent: 'flex-end',
    alignItems: 'center',
    paddingBottom: Spacing.group,
    zIndex: 10,
  },
  scanHintPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    backgroundColor: 'rgba(20, 18, 11, 0.75)',
    borderWidth: 1,
    borderColor: c.goldLine,
    paddingHorizontal: Spacing.pane,
    paddingVertical: Spacing.md,
    borderRadius: Radius.pill,
  },
  scanHintText: { color: c.text, fontSize: 13, fontWeight: '500' },
  infoText: {
    color: c.textSecondary,
    fontSize: 13,
    lineHeight: 18,
    textAlign: 'center',
    paddingHorizontal: Spacing.md,
  },

  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(20, 18, 11, 0.72)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    backgroundColor: c.backgroundElement,
    width: '100%',
    borderTopLeftRadius: Radius.sheet,
    borderTopRightRadius: Radius.sheet,
    borderWidth: 1,
    borderColor: c.border,
    borderBottomWidth: 0,
    padding: Spacing.screen,
    paddingBottom: Spacing.group + 8,
    alignItems: 'center',
  },
  modalPreRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginBottom: Spacing.md },
  modalPre: { fontSize: 12, color: c.gold, fontWeight: '500', letterSpacing: 0.3 },
  modalTitle: {
    fontSize: 20,
    fontWeight: '500',
    color: c.text,
    textAlign: 'center',
    marginBottom: Spacing.xs,
  },
  modalAuthor: { fontSize: 15, color: c.textSecondary, marginBottom: Spacing.screen, textAlign: 'center' },
  saveButton: {
    backgroundColor: c.primaryButtonFill,
    width: '100%',
    paddingVertical: Spacing.pane,
    borderRadius: Radius.pill,
    alignItems: 'center',
  },
  saveButtonText: { color: c.primaryButtonText, fontWeight: '500', fontSize: 16 },
  cancelPress: { marginTop: Spacing.pane },
  cancelText: { color: c.textSecondary, textAlign: 'center', fontSize: 14 },
});
