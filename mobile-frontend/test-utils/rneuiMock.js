const React = require("react");
const {
  Text: NativeText,
  TextInput,
  TouchableOpacity,
  View,
} = require("react-native");

const Input = ({ testID, placeholder, value, onChangeText, label, disabled }) =>
  React.createElement(TextInput, {
    testID: testID || `input-${placeholder}`,
    placeholder,
    value,
    onChangeText,
    editable: !disabled,
    accessibilityLabel: label,
  });

const Button = ({ testID, title, onPress, disabled }) =>
  React.createElement(
    TouchableOpacity,
    {
      testID: testID || `button-${title}`,
      onPress: disabled ? undefined : onPress,
      disabled: Boolean(disabled),
      accessibilityState: { disabled: Boolean(disabled) },
    },
    React.createElement(NativeText, null, title),
  );

const ListItem = ({ testID, onPress, children }) =>
  React.createElement(
    TouchableOpacity,
    { testID, onPress },
    React.createElement(View, null, children),
  );
ListItem.Content = ({ children }) => React.createElement(View, null, children);
ListItem.Title = ({ children }) =>
  React.createElement(NativeText, null, children);
ListItem.Subtitle = ({ children }) =>
  React.createElement(NativeText, null, children);
ListItem.Chevron = () => null;

const Card = ({ children }) => React.createElement(View, null, children);
Card.Title = ({ children }) => React.createElement(NativeText, null, children);
Card.Divider = () => null;

const SearchBar = ({ testID, placeholder, value, onChangeText }) =>
  React.createElement(TextInput, {
    testID: testID || "search-bar",
    placeholder,
    value,
    onChangeText,
  });

const ButtonGroup = ({ buttons, selectedIndex, onPress }) =>
  React.createElement(
    View,
    null,
    buttons.map((label, index) =>
      React.createElement(
        TouchableOpacity,
        {
          key: label,
          testID: `view-${label}`,
          accessibilityState: { selected: index === selectedIndex },
          onPress: () => onPress(index),
        },
        React.createElement(NativeText, null, label),
      ),
    ),
  );

const theme = {
  mode: "light",
  colors: {
    primary: "#007AFF",
    white: "#ffffff",
    black: "#000000",
    background: "#f5f5f5",
    grey0: "#393e42",
    grey1: "#43484d",
    grey2: "#5e6977",
    success: "#52c41a",
    error: "#ff190c",
  },
};

module.exports = {
  __esModule: true,
  Button,
  ButtonGroup,
  Card,
  Divider: () => null,
  Icon: () => null,
  Input,
  ListItem,
  SearchBar,
  Text: NativeText,
  useTheme: () => ({ theme }),
};
