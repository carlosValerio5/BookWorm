import { DarkTheme, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';

import { AnimatedSplashOverlay } from '@/components/animated-icon';
import AppTabs from '@/components/app-tabs';
import { BookProvider } from '@/context/BookContext';

SplashScreen.preventAutoHideAsync();

export default function TabLayout() {
    return (
        <ThemeProvider value={DarkTheme}>
            <BookProvider>
                <AnimatedSplashOverlay />
                <AppTabs />
            </BookProvider>
        </ThemeProvider>
    );
}