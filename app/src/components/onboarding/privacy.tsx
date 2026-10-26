import { StyleSheet, View } from 'react-native';

import { Card } from '@/components/card';
import { Expandable } from '@/components/expandable';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';

/**
 * The three privacy screens at sign-up (docs/privacy_texts.md Part 1, D-91; PDPA notice and choice:
 * nothing is collected before the user goes on). Drafts for Patrick's review (PV1-PV5). The sentence
 * about pasting bank messages is left out while the parser isn't built (PV4). Each card shows its main
 * point; the rest is one tap away.
 */
export function PrivacyNotice() {
  return (
    <View style={styles.wrap}>
      <Card title="What FAST sees, and never sees">
        <ThemedText type="smallBold">FAST sees only what you tell it.</ThemedText>
        <ThemedText type="small">
          It never asks for your bank login, password, TAC or OTP, your full card or account numbers, your IC number,
          or your contacts, photos, location or messages. It has no connection to your bank and can&apos;t move money.
        </ThemedText>
        <Expandable label="What you enter, and what FAST works out">
          <Bullets lines={['The answers you give now: your type of work, income, usual costs, debts and savings goal',
            'The money in and out that you type in', 'Your monthly check-in: what you have and what you owe',
            'What you do in the game: plants and decorations']} />
          <ThemedText type="small">From that, for you only: your band, health score, forecast and advice, your points and garden.</ThemedText>
        </Expandable>
      </Card>

      <Card title="Our scam-safety promise">
        <ThemedText type="small">
          FAST will never ask for your bank password, TAC or OTP, ask you to transfer money or &quot;verify&quot; your
          account, call, WhatsApp or SMS you, or send you a link to log in. Anyone who does is a scam.
        </ThemedText>
        <Expandable label="If you think you've been scammed">
          <Bullets lines={['Call the National Scam Response Centre at 997 straight away: the sooner, the better the chance your money can be stopped',
            'Call your bank\'s hotline to block your card or account', 'Make a police report']} />
          <ThemedText type="small">Check a phone number or bank account before you pay, at PDRM&apos;s Semak Mule website.</ThemedText>
        </Expandable>
      </Card>

      <Card title="Your data">
        <ThemedText type="small">
          Only you can see your data. It is stored in Singapore. No ads, no selling, no sharing with lenders or anyone else.
          You can delete your account, and everything with it, at any time.
        </ThemedText>
        <Expandable label="Who sees what, and for how long">
          <Bullets lines={['The money helper (AI) gets only a short summary of your results and the question you type, with card, account, IC and phone numbers and emails removed. FAST keeps neither. The AI service (Groq) may process them outside Malaysia',
            'The details of your entries are deleted after 36 months; each month\'s check-in totals are kept for your game',
            'You can fix or delete an entry for 48 hours; after that it is locked',
            'FAST only knows what you enter: its results are only as good as your entries']} />
        </Expandable>
      </Card>
    </View>
  );
}

function Bullets({ lines }: { lines: string[] }) {
  return <>{lines.map((l) => <ThemedText key={l} type="small">• {l}</ThemedText>)}</>;
}

const styles = StyleSheet.create({
  wrap: { gap: Spacing.two + Spacing.one },
});
