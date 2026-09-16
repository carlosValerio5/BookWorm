import { useState, useRef } from 'react';
import { StyleSheet, Pressable, View, Text, ActivityIndicator, Modal } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { Image } from 'expo-image';
import { realBookScan } from '../services/api';
import { useBooks } from '../context/BookContext';

export default function HomeScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [loading, setLoading] = useState(false);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const cameraRef = useRef<any>(null);
  const [foundBook, setFoundBook] = useState<any>(null);
  const { addBook } = useBooks();

  const encenderCamara = async () => {
    setErrorMessage(null);
    if (!permission?.granted) await requestPermission();
    setIsCameraActive(true);
  };

  const escanearLibroReal = async () => {
    if (loading) return;
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
          setErrorMessage(resultado.message || "No se pudo reconocer el libro. Intenta enfocar mejor la portada.");
          setIsCameraActive(false);
        }
      }
    } catch (error) {
      console.error("Error al capturar:", error);
      setErrorMessage("Error al procesar la foto. Intenta de nuevo.");
      setIsCameraActive(false);
    } finally {
      setLoading(false);
    }
  };

  const guardarLibro = () => {
    if (foundBook) {
      const bookToSave = {
        title: foundBook.title,
        author: foundBook.author,
        isbn: foundBook.isbn,
        coverImage: foundBook.coverImage,
      };

      addBook(bookToSave);
      setFoundBook(null);
      alert("¡Libro guardado en tu biblioteca!");
    }
  };

  return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>

          <View style={styles.header}>
            <Text style={styles.title}>BookWorm</Text>
            <Text style={styles.version}>v0.1.0</Text>
          </View>

          {errorMessage && (
              <View style={styles.errorBanner}>
                <Text style={styles.errorBannerText}>⚠️ {errorMessage}</Text>
              </View>
          )}

          {!isCameraActive ? (
              <Pressable style={styles.cameraBoxPlaceholder} onPress={encenderCamara}>
                <View style={styles.dot} />
                <Text style={styles.cameraTitle}>Escanear Portada o Contraportada</Text>
                <Text style={styles.cameraSubtitle}>Toca aquí para abrir la cámara</Text>
              </Pressable>
          ) : (
              <View style={styles.cameraBoxActive}>
                {permission?.granted ? (
                    <>
                      <CameraView style={styles.camera} facing="back" ref={cameraRef} />
                      <Pressable style={styles.cameraOverlayAbsolute} onPress={escanearLibroReal}>
                        {loading ? (
                            <ActivityIndicator size="large" color="#FFF" />
                        ) : (
                            <Text style={styles.scanHintText}>Enfoca el libro y toca para identificar...</Text>
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

                {foundBook?.coverImage && (
                    <Image source={{ uri: foundBook.coverImage }} style={styles.modalCoverImage} />
                )}

                <Text style={styles.modalPre}>¡Encontramos una coincidencia!</Text>
                <Text style={styles.modalTitle}>{foundBook?.title}</Text>
                <Text style={styles.modalAuthor}>{foundBook?.author}</Text>
                <Text style={styles.modalIsbn}>ISBN: {foundBook?.isbn}</Text>

                <Pressable style={styles.saveButton} onPress={guardarLibro}>
                  <Text style={styles.saveButtonText}>Guardar en mi biblioteca</Text>
                </Pressable>

                <Pressable onPress={() => setFoundBook(null)} style={{ marginTop: 12 }}>
                  <Text style={{ color: '#7B9EAD', textAlign: 'center' }}>Cancelar</Text>
                </Pressable>
              </View>
            </View>
          </Modal>

        </SafeAreaView>
      </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#EAF6F9' },
  safeArea: { flex: 1, paddingHorizontal: 20, justifyContent: 'space-between', paddingVertical: 15 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { fontSize: 24, fontWeight: 'bold', fontFamily: 'serif', color: '#0A2540' },
  version: { color: '#7B9EAD', fontSize: 14 },

  errorBanner: { backgroundColor: '#FEE2E2', borderWidth: 1, borderColor: '#F87171', padding: 10, borderRadius: 12 },
  errorBannerText: { color: '#991B1B', fontSize: 13, fontWeight: '600', textAlign: 'center' },
  cameraBoxPlaceholder: {
    backgroundColor: '#FFFFFF',
    borderWidth: 2,
    borderColor: '#82C1D4',
    borderStyle: 'dashed',
    borderRadius: 24,
    width: '100%',
    height: '90%',
    alignSelf: 'center',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 3,
  },
  dot: { width: 14, height: 14, borderRadius: 7, backgroundColor: '#60A5FA', marginBottom: 14 },
  cameraTitle: { fontSize: 19, fontWeight: 'bold', color: '#0A2540', marginBottom: 6, textAlign: 'center' },
  cameraSubtitle: { color: '#7B9EAD', fontSize: 13, textAlign: 'center' },

  cameraBoxActive: {
    width: '100%',
    height: '90%',
    borderRadius: 24,
    overflow: 'hidden',
    alignSelf: 'center',
    borderWidth: 2,
    borderColor: '#82C1D4',
    position: 'relative'
  },
  camera: { flex: 1 },
  cameraOverlayAbsolute: {
    ...StyleSheet.absoluteFill,
    backgroundColor: 'rgba(0,0,0,0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  scanHintText: { color: '#FFF', backgroundColor: 'rgba(0,0,0,0.65)', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 10, fontSize: 13, fontWeight: '500' },
  infoText: { color: '#7B9EAD', fontSize: 13, lineHeight: 18, textAlign: 'center', paddingHorizontal: 10 },

  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalCard: { backgroundColor: '#FFF', width: '100%', borderRadius: 20, padding: 24, alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.2, elevation: 5 },
  modalCoverImage: { width: 100, height: 140, borderRadius: 8, marginBottom: 16, backgroundColor: '#E2E8F0' },
  modalPre: { fontSize: 12, color: '#607D8B', fontWeight: '600', marginBottom: 8 },
  modalTitle: { fontSize: 22, fontFamily: 'serif', fontWeight: 'bold', color: '#0A2540', textAlign: 'center', marginBottom: 4 },
  modalAuthor: { fontSize: 16, color: '#4A5568', marginBottom: 12, textAlign: 'center' },
  modalIsbn: { fontSize: 12, fontFamily: 'monospace', color: '#A0AEC0', marginBottom: 24 },
  saveButton: { backgroundColor: '#1B2635', width: '100%', paddingVertical: 14, borderRadius: 12, alignItems: 'center' },
  saveButtonText: { color: '#FFF', fontWeight: 'bold', fontSize: 16 },
});