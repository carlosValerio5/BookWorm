import { StyleSheet, View, Text, Pressable, FlatList } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useBooks } from '../context/BookContext';
import { StarAccent } from '@/components/star-accent';
import { Colors, Radius, Spacing, spineColorForIsbn } from '@/constants/theme';

const c = Colors.dark;

export default function BibliotecaScreen() {
  const router = useRouter();
  const { books } = useBooks();

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <View>
            <View style={styles.preTitleRow}>
              <StarAccent size={10} dim />
              <Text style={styles.preTitle}>MI COLECCIÓN</Text>
            </View>
            <Text style={styles.title}>Biblioteca</Text>
          </View>
          <View style={styles.countBadge}>
            <Text style={styles.countText}>
              {books.length} {books.length === 1 ? 'libro' : 'libros'}
            </Text>
          </View>
        </View>

        {books.length === 0 ? (
          <View style={styles.emptyState}>
            <View style={styles.starsRow}>
              <StarAccent size={16} dim />
              <StarAccent size={22} />
              <StarAccent size={16} dim />
            </View>
            <View style={styles.booksIllustration}>
              <View style={[styles.bookCard, styles.bookLeft]}>
                <View style={styles.bookSpine} />
              </View>
              <View style={[styles.bookCard, styles.bookRight]}>
                <View style={styles.bookSpine} />
              </View>
              <View style={[styles.bookCard, styles.bookCenter]}>
                <View style={[styles.bookSpine, styles.bookSpineBright]} />
              </View>
            </View>

            <Text style={styles.emptySubtitle}>
              Escanea tu primer libro y aparecerá aquí, como en un catálogo de achados.
            </Text>

            <Pressable style={styles.scanButton} onPress={() => router.navigate('/')}>
              <StarAccent size={12} />
              <Text style={styles.scanButtonText}>Escanear un libro</Text>
            </Pressable>
          </View>
        ) : (
          <FlatList
            data={books}
            keyExtractor={(item) => item.id}
            contentContainerStyle={styles.listContent}
            renderItem={({ item }) => (
              <View style={styles.bookItemCard}>
                <View
                  style={[styles.bookColorStripe, { backgroundColor: spineColorForIsbn(item.isbn ?? item.id) }]}
                />
                <View style={styles.bookItemBody}>
                  <Text style={styles.bookItemTitle}>{item.title}</Text>
                  <Text style={styles.bookItemAuthor}>{item.author}</Text>
                  <Text style={styles.bookItemIsbn}>ISBN {item.isbn}</Text>
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
  container: { flex: 1, backgroundColor: c.background },
  safeArea: { flex: 1, paddingHorizontal: Spacing.screen, paddingTop: Spacing.group },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: Spacing.md,
  },
  preTitleRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.xs, marginBottom: Spacing.xs },
  preTitle: {
    fontSize: 12,
    fontWeight: '500',
    color: c.gold,
    letterSpacing: 0.6,
  },
  title: { fontSize: 28, fontWeight: '500', color: c.text },
  countBadge: {
    backgroundColor: c.backgroundElement,
    borderWidth: 1,
    borderColor: c.goldLine,
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.pane,
    borderRadius: Radius.pill,
  },
  countText: { color: c.text, fontWeight: '500', fontSize: 13, fontVariant: ['tabular-nums'] },
  emptyState: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingBottom: 40 },
  starsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.pane,
    marginBottom: Spacing.md,
  },
  booksIllustration: {
    height: 160,
    width: 200,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.group,
  },
  bookCard: {
    width: 88,
    height: 128,
    borderRadius: Radius.row,
    position: 'absolute',
    backgroundColor: c.backgroundElement,
    borderWidth: 1,
    borderColor: c.border,
    overflow: 'hidden',
  },
  bookSpine: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    width: 6,
    backgroundColor: c.goldDeep,
  },
  bookSpineBright: { backgroundColor: c.gold },
  bookLeft: { transform: [{ rotate: '-10deg' }, { translateX: -32 }] },
  bookRight: { transform: [{ rotate: '10deg' }, { translateX: 32 }] },
  bookCenter: { height: 136, zIndex: 10 },
  emptySubtitle: {
    color: c.textSecondary,
    fontSize: 15,
    textAlign: 'center',
    paddingHorizontal: Spacing.group,
    lineHeight: 22,
    marginBottom: Spacing.group,
  },
  scanButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    backgroundColor: c.primaryButtonFill,
    paddingVertical: Spacing.pane,
    paddingHorizontal: Spacing.screen,
    borderRadius: Radius.pill,
  },
  scanButtonText: { color: c.primaryButtonText, fontWeight: '500', fontSize: 16 },
  listContent: { paddingVertical: Spacing.group },
  bookItemCard: {
    backgroundColor: c.backgroundElement,
    borderRadius: Radius.row,
    borderWidth: 1,
    borderColor: c.border,
    padding: Spacing.pane,
    flexDirection: 'row',
    marginBottom: Spacing.md,
    alignItems: 'center',
  },
  bookColorStripe: { width: 6, height: 44, borderRadius: 3 },
  bookItemBody: { flex: 1, marginLeft: Spacing.pane },
  bookItemTitle: { fontSize: 16, fontWeight: '500', color: c.text },
  bookItemAuthor: { fontSize: 14, color: c.textSecondary, marginTop: Spacing.hair },
  bookItemIsbn: {
    fontSize: 11,
    fontFamily: 'monospace',
    color: c.textTertiary,
    marginTop: Spacing.xs,
  },
});
