import { NativeTabs } from 'expo-router/unstable-native-tabs';

import { Colors } from '@/constants/theme';

const c = Colors.dark;

export default function AppTabs() {
  return (
    <NativeTabs
      backgroundColor={c.backgroundElement}
      indicatorColor={c.goldLine}
      labelStyle={{ selected: { color: c.gold } }}>
      <NativeTabs.Trigger name="index">
        <NativeTabs.Trigger.Label>Escanear</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          src={require('@/assets/images/tabIcons/home.png')}
          renderingMode="template"
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="biblioteca">
        <NativeTabs.Trigger.Label>Biblioteca</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          src={require('@/assets/images/tabIcons/explore.png')}
          renderingMode="template"
        />
      </NativeTabs.Trigger>
    </NativeTabs>
  );
}
