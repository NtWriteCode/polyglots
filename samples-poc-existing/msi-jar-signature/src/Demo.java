import javax.swing.JOptionPane;

/** Benign PoC payload: pops a message box so you can see the JAR side ran. */
public class Demo {
    public static void main(String[] args) {
        JOptionPane.showMessageDialog(
            null,
            "Polyglot demo: the JAR half executed.\n"
          + "This is a harmless MessageBox for a presentation.",
            "MSI + JAR PoC",
            JOptionPane.INFORMATION_MESSAGE);
    }
}
