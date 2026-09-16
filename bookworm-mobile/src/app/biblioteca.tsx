import { StyleSheet, View, Text, Pressable, FlatList } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useBooks } from '../context/BookContext';

export default function BibliotecaScreen() {
  const router = useRouter();
  const { books } = useBooks();

  return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.header}>
            <View>
              <Text style={styles.preTitle}>MI COLECCIÓN</Text>
              <Text style={styles.title}>Biblioteca</Text>
            </View>
            <View style={styles.countBadge}>
              <Text style={styles.countText}>{books.length} {books.length === 1 ? 'libro' : 'libros'}</Text>
            </View>
          </View>

          {books.length === 0 ? (
              <View style={styles.emptyState}>
                <View style={styles.booksIllustration}>
                  <View style={[styles.bookCard, styles.bookLeft]} />
                  <View style={[styles.bookCard, styles.bookRight]} />
                  <View style={[styles.bookCard, styles.bookCenter]} />
                </View>

                <Text style={styles.emptySubtitle}>
                  Escanea tu primer libro y su foto aparecerá aquí.
                </Text>

                <Pressable style={styles.scanButton} onPress={() => router.navigate('/')}>
                  <Text style={styles.scanButtonText}>[+] Escanear un libro</Text>
                </Pressable>
              </View>
          ) : (
              /* Lista de libros registrados */
              <FlatList
                  data={books}
                  keyExtractor={(item) => item.id}
                  contentContainerStyle={{ paddingVertical: 20 }}
                  renderItem={({ item }) => (
                      <View style={styles.bookItemCard}>
                        <View style={styles.bookColorStripe} />
                        <View style={{ flex: 1, marginLeft: 12 }}>
                          <Text style={styles.bookItemTitle}>{item.title}</Text>
                          <Text style={styles.bookItemAuthor}>{item.author}</Text>
                          <Text style={styles.bookItemIsbn}>ISBN: {item.isbn}</Text>
                        </View>
                      </View>
                  )}
              />
          )}

        </SafeAreaView>
      </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#EAF6F9' },
  safeArea: { flex: 1, paddingHorizontal: 24, paddingTop: 20 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 },
  preTitle: { fontSize: 12, fontWeight: '600', color: '#607D8B', marginBottom: 4, letterSpacing: 0.5 },
  title: { fontSize: 32, fontWeight: 'bold', fontFamily: 'serif', color: '#0A2540' },
  countBadge: { backgroundColor: '#FFF', paddingVertical: 6, paddingHorizontal: 12, borderRadius: 20 },
  countText: { color: '#0A2540', fontWeight: '600', fontSize: 14 },
  emptyState: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingBottom: 40 },
  booksIllustration: { height: 180, width: 200, justifyContent: 'center', alignItems: 'center', marginBottom: 30 },
  bookCard: { width: 100, height: 140, borderRadius: 8, position: 'absolute' },
  bookLeft: { backgroundColor: '#F39C9C', transform: [{ rotate: '-10deg' }, { translateX: -35 }] },
  bookRight: { backgroundColor: '#F7B7B7', transform: [{ rotate: '10deg' }, { translateX: 35 }] },
  bookCenter: { backgroundColor: '#7CD1E8', height: 150, zIndex: 10 },
  emptyTitle: { fontSize: 22, fontFamily: 'serif', color: '#0A2540', fontWeight: 'bold', marginBottom: 12 },
  emptySubtitle: { color: '#7B9EAD', fontSize: 15, textAlign: 'center', paddingHorizontal: 20, lineHeight: 22, marginBottom: 30 },
  scanButton: { backgroundColor: '#1B2635', paddingVertical: 14, paddingHorizontal: 30, borderRadius: 30 },
  scanButtonText: { color: '#FFF', fontWeight: 'bold', fontSize: 16 },
  bookItemCard: { backgroundColor: '#FFF', borderRadius: 12, padding: 16, flexDirection: 'row', marginBottom: 12, alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.05, elevation: 2 },
  bookColorStripe: { width: 6, height: 40, backgroundColor: '#82D2E5', borderRadius: 3 },
  bookItemTitle: { fontSize: 16, fontWeight: 'bold', color: '#0A2540' },
  bookItemAuthor: { fontSize: 14, color: '#4A5568', marginTop: 2 },
  bookItemIsbn: { fontSize: 11, fontFamily: 'monospace', color: '#7B9EAD', marginTop: 4 },
});