import { Button, Card, Input, Text } from "@rneui/themed";
import { useState } from "react";
import { ActivityIndicator, Alert, StyleSheet, View } from "react-native";
import apiService from "../../services/apiService";

const CreatePortfolioScreen = ({ navigation }) => {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [currency, setCurrency] = useState("USD"); // Default or allow selection
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCreate = async () => {
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("Portfolio name is required.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await apiService.createPortfolio({
        name: trimmedName,
        description: description.trim(),
        currency: currency.trim().toUpperCase() || "USD",
      });
      // Navigate back to portfolio list or to the new portfolio's detail screen
      // PortfolioListScreen should refresh on focus to show the new portfolio
      navigation.goBack();
    } catch (err) {
      console.error("Failed to create portfolio:", err);
      setError("Could not create portfolio. Please try again.");
      Alert.alert(
        "Error",
        "Could not create portfolio. Please try again later.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Card containerStyle={styles.card}>
        {/* Card.Title is set in navigation options */}
        <Input
          testID="portfolio-name-input"
          placeholder="Portfolio Name (e.g., Growth Fund)"
          label="Name *"
          onChangeText={setName}
          value={name}
          containerStyle={styles.inputContainer}
          disabled={loading}
        />
        <Input
          testID="portfolio-description-input"
          placeholder="Optional description"
          label="Description"
          onChangeText={setDescription}
          value={description}
          containerStyle={styles.inputContainer}
          multiline
          numberOfLines={3}
          disabled={loading}
        />
        <Input
          testID="portfolio-currency-input"
          placeholder="Currency Code (e.g., USD)"
          label="Currency"
          onChangeText={setCurrency} // Consider a picker for common currencies
          value={currency}
          containerStyle={styles.inputContainer}
          disabled={loading}
          autoCapitalize="characters"
        />
        {error ? (
          <Text testID="create-error" style={styles.errorText}>
            {error}
          </Text>
        ) : null}
        {loading ? (
          <ActivityIndicator
            testID="loading-indicator"
            size="large"
            color="#007AFF"
            style={styles.loader}
          />
        ) : (
          <Button
            testID="create-portfolio-submit"
            title="Create Portfolio"
            onPress={handleCreate}
            buttonStyle={styles.button}
            disabled={!name.trim()}
          />
        )}
      </Card>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f5f5f5",
    paddingTop: 20, // Add padding if header is not shown or for spacing
  },
  card: {
    borderRadius: 10,
  },
  inputContainer: {
    marginBottom: 15,
  },
  button: {
    backgroundColor: "#007AFF",
    borderRadius: 8,
    marginTop: 10,
    paddingVertical: 12,
  },
  errorText: {
    color: "red",
    textAlign: "center",
    marginBottom: 10,
  },
  loader: {
    marginTop: 10,
  },
});

export default CreatePortfolioScreen;
