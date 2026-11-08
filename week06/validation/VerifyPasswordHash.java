import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

/** Check the actual hash read back from the isolated MySQL signup test. */
class VerifyPasswordHash {
    public static void main(String[] args) {
        if (args.length != 1 || args[0].length() != 60
                || !new BCryptPasswordEncoder().matches("Movie123!", args[0])) {
            throw new AssertionError("Persisted signup password did not match the bcrypt contract");
        }
        System.out.println("PASS: stored bcrypt hash matches the test signup password");
    }
}
