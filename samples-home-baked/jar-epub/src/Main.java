import java.awt.GraphicsEnvironment;
import javax.swing.JOptionPane;

public class Main {
    public static void main(String[] args) {
        String msg = "This came from the JAR side of the polyglot";
        System.out.println(msg);
        // Show the dialog only when there is a display, so `java -jar` also works headless.
        if (!GraphicsEnvironment.isHeadless()) {
            JOptionPane.showMessageDialog(null, msg, "Polyglot POC", JOptionPane.INFORMATION_MESSAGE);
        }
    }
}
